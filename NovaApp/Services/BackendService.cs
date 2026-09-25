using System.Collections.Concurrent;
using System.Diagnostics;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using NovaApp.Models;

namespace NovaApp.Services;

/// <summary>
/// nova_bridge.py sürecini başlatır ve JSON Lines protokolüyle konuşur.
/// Yazma işlemleri kilitlidir (telemetri zamanlayıcısı ve sohbet aynı anda yazabilir).
/// </summary>
public sealed class BackendService : IDisposable
{
    private Process? _process;
    private StreamWriter? _writer;
    private readonly SemaphoreSlim _writeLock = new(1, 1);
    private readonly ConcurrentDictionary<int, TaskCompletionSource<JsonElement>> _pending = new();
    private readonly ConcurrentQueue<string> _stderrTail = new();
    private int _requestId;
    private bool _stopping;

    public event Action<string, string>? ReadyReceived;                   // version, device
    public event Action<TelemetryPacket>? TelemetryReceived;
    public event Action<int, string, bool, string, string?>? ChunkReceived; // id, chunk, done, reply, action
    public event Action<string>? ErrorReceived;
    public event Action<bool>? ConnectionStateChanged;

    public bool IsRunning => _process is { HasExited: false };

    /// <summary>Hata mesajlarının dili (arayüz dili değişince güncellenir).</summary>
    public bool English { get; set; }

    private string L(string tr, string en) => English ? en : tr;

    public static string AppRoot
    {
        get
        {
            var env = Environment.GetEnvironmentVariable("NOVA_HOME");
            if (!string.IsNullOrEmpty(env) && File.Exists(Path.Combine(env, "nova_bridge.py")))
                return env;
            for (var dir = new DirectoryInfo(AppContext.BaseDirectory); dir != null; dir = dir.Parent)
                if (File.Exists(Path.Combine(dir.FullName, "nova_bridge.py")))
                    return dir.FullName;
            return Directory.GetCurrentDirectory();
        }
    }

    public static string ResolvePython(string root)
    {
        var env = Environment.GetEnvironmentVariable("NOVA_PYTHON");
        if (!string.IsNullOrEmpty(env) && File.Exists(env)) return env;
        foreach (var venv in new[] { ".venv", "venv", "nova_env" })
        {
            var py = Path.Combine(root, venv, "bin", "python");
            if (File.Exists(py)) return py;
        }
        return "python3";
    }

    public async Task<bool> StartAsync()
    {
        try
        {
            var root = AppRoot;
            var psi = new ProcessStartInfo
            {
                FileName = ResolvePython(root),
                WorkingDirectory = root,
                RedirectStandardInput = true,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                UseShellExecute = false,
                CreateNoWindow = true,
                StandardOutputEncoding = Encoding.UTF8,
                StandardErrorEncoding = Encoding.UTF8,
            };
            psi.ArgumentList.Add("-u");
            psi.ArgumentList.Add(Path.Combine(root, "nova_bridge.py"));
            psi.Environment["PYTHONIOENCODING"] = "utf-8";
            psi.Environment["PYTHONUNBUFFERED"] = "1";

            _stopping = false;
            _process = new Process { StartInfo = psi, EnableRaisingEvents = true };
            _process.Exited += (_, _) =>
            {
                ConnectionStateChanged?.Invoke(false);
                if (!_stopping)
                    ErrorReceived?.Invoke(L("Nova motoru beklenmedik şekilde kapandı:", "The Nova engine stopped unexpectedly:") +
                                          "\n" + string.Join("\n", _stderrTail.TakeLast(8)));
                foreach (var tcs in _pending.Values) tcs.TrySetCanceled();
                _pending.Clear();
            };
            _process.Start();
            _writer = new StreamWriter(_process.StandardInput.BaseStream, new UTF8Encoding(false)) { AutoFlush = true };

            _ = Task.Run(() => ReadStdoutAsync(_process.StandardOutput));
            _ = Task.Run(() => ReadStderrAsync(_process.StandardError));
            ConnectionStateChanged?.Invoke(true);
            await Task.CompletedTask;
            return true;
        }
        catch (Exception ex)
        {
            ErrorReceived?.Invoke(L($"Nova motoru başlatılamadı: {ex.Message}\nPython ortamını kurmak için: ./install.sh",
                                    $"Could not start the Nova engine: {ex.Message}\nSet up the Python environment with: ./install.sh"));
            ConnectionStateChanged?.Invoke(false);
            return false;
        }
    }

    private async Task ReadStdoutAsync(StreamReader reader)
    {
        try
        {
            while (await reader.ReadLineAsync() is { } line)
            {
                if (line.Length > 1 && line[0] == '{')
                    Dispatch(line);
            }
        }
        catch (Exception ex) when (ex is IOException or ObjectDisposedException) { }
    }

    private async Task ReadStderrAsync(StreamReader reader)
    {
        try
        {
            while (await reader.ReadLineAsync() is { } line)
            {
                Debug.WriteLine($"[nova] {line}");
                _stderrTail.Enqueue(line);
                while (_stderrTail.Count > 60) _stderrTail.TryDequeue(out _);
            }
        }
        catch (Exception ex) when (ex is IOException or ObjectDisposedException) { }
    }

    private void Dispatch(string json)
    {
        try
        {
            using var doc = JsonDocument.Parse(json);
            var root = doc.RootElement;
            var type = root.TryGetProperty("type", out var t) ? t.GetString() : null;

            if (root.TryGetProperty("id", out var idProp) && idProp.ValueKind == JsonValueKind.Number)
            {
                var id = idProp.GetInt32();
                if (type == "chat_chunk")
                {
                    ChunkReceived?.Invoke(id,
                        Str(root, "chunk"),
                        root.TryGetProperty("done", out var d) && d.ValueKind == JsonValueKind.True,
                        Str(root, "reply"),
                        root.TryGetProperty("action", out var a) && a.ValueKind == JsonValueKind.String ? a.GetString() : null);
                    return;
                }
                if (_pending.TryRemove(id, out var tcs))
                    tcs.TrySetResult(root.Clone());
            }

            switch (type)
            {
                case "ready":
                    ReadyReceived?.Invoke(Str(root, "version"), Str(root, "device"));
                    break;
                case "telemetry":
                    if (JsonSerializer.Deserialize<TelemetryPacket>(json) is { } packet)
                        TelemetryReceived?.Invoke(packet);
                    break;
                case "error":
                    ErrorReceived?.Invoke(Str(root, "message"));
                    break;
            }
        }
        catch (JsonException ex)
        {
            Debug.WriteLine($"JSON hatası: {ex.Message}");
        }
    }

    private static string Str(JsonElement e, string name) =>
        e.TryGetProperty(name, out var p) && p.ValueKind == JsonValueKind.String ? p.GetString() ?? "" : "";

    private async Task<int> WriteAsync(JsonObject payload)
    {
        var id = Interlocked.Increment(ref _requestId);
        payload["id"] = id;
        if (_writer == null || !IsRunning) return -1;
        await _writeLock.WaitAsync();
        try { await _writer.WriteLineAsync(payload.ToJsonString()); }
        catch (IOException) { return -1; }
        finally { _writeLock.Release(); }
        return id;
    }

    /// <summary>İstek gönderir ve aynı id'li ilk yanıtı bekler.</summary>
    public async Task<JsonElement?> RequestAsync(JsonObject payload, int timeoutMs = 10000)
    {
        if (!IsRunning) return null;
        var id = Interlocked.Increment(ref _requestId);
        var tcs = new TaskCompletionSource<JsonElement>(TaskCreationOptions.RunContinuationsAsynchronously);
        _pending[id] = tcs;
        payload["id"] = id;
        try
        {
            await _writeLock.WaitAsync();
            try { await _writer!.WriteLineAsync(payload.ToJsonString()); }
            finally { _writeLock.Release(); }
            return await tcs.Task.WaitAsync(TimeSpan.FromMilliseconds(timeoutMs));
        }
        catch (Exception) { return null; }
        finally { _pending.TryRemove(id, out _); }
    }

    private static JsonObject Act(string action) => new() { ["action"] = action };

    // ── Kısayollar ───────────────────────────────────────────────────────────
    public Task<int> SendChatAsync(string prompt) => WriteAsync(new JsonObject { ["action"] = "chat", ["prompt"] = prompt });
    public Task<int> RequestTelemetryAsync() => WriteAsync(Act("telemetry"));

    public async Task<string> CommandAsync(string command, int timeoutMs = 30000)
    {
        var res = await RequestAsync(new JsonObject { ["action"] = "command", ["command"] = command }, timeoutMs);
        return res is { } r ? Str(r, "reply") : "";
    }

    public async Task<List<ChatMessage>> GetHistoryAsync(int limit = 40)
    {
        var list = new List<ChatMessage>();
        var res = await RequestAsync(new JsonObject { ["action"] = "get_history", ["limit"] = limit });
        if (res is { } r && r.TryGetProperty("messages", out var arr) && arr.ValueKind == JsonValueKind.Array)
        {
            foreach (var m in arr.EnumerateArray())
            {
                var zaman = Str(m, "zaman");
                list.Add(new ChatMessage
                {
                    Role = Str(m, "rol") switch { "kullanici" => "user", "nova" => "nova", _ => "system" },
                    Text = Str(m, "icerik"),
                    Timestamp = zaman.Length >= 16 ? zaman[11..16] : zaman,
                });
            }
        }
        return list;
    }

    public Task SpeakAsync(string text) => RequestAsync(new JsonObject { ["action"] = "speak", ["text"] = text });
    public Task StopSpeakingAsync() => RequestAsync(Act("stop_speaking"));
    public Task ReadHistoryAsync(int count = 3) => RequestAsync(new JsonObject { ["action"] = "read_history", ["count"] = count });

    public async Task<string> ListenAsync(int timeout = 7)
    {
        var res = await RequestAsync(new JsonObject { ["action"] = "listen", ["timeout"] = timeout }, (timeout + 20) * 1000);
        return res is { } r ? Str(r, "text") : "";
    }

    public async Task<string> ObserveScreenAsync(string prompt, bool speak)
    {
        var res = await RequestAsync(new JsonObject { ["action"] = "observe_screen", ["prompt"] = prompt, ["speak"] = speak }, 60000);
        return res is { } r ? Str(r, "text") : "";
    }

    public async Task<(NovaSettings Settings, string WebToken)> GetSettingsAsync()
    {
        var res = await RequestAsync(Act("get_settings"));
        if (res is { } r && r.TryGetProperty("settings", out var s))
            return (JsonSerializer.Deserialize<NovaSettings>(s.GetRawText()) ?? new(), Str(r, "web_token"));
        return (new NovaSettings(), "");
    }

    public async Task<bool> SaveSettingsAsync(NovaSettings settings)
    {
        var node = JsonSerializer.SerializeToNode(settings);
        var res = await RequestAsync(new JsonObject { ["action"] = "save_settings", ["settings"] = node });
        return res is { } r && r.TryGetProperty("restart_required", out var rr) && rr.ValueKind == JsonValueKind.True;
    }

    public async Task<bool> SetTrainingAsync(bool active) =>
        await RequestAsync(Act(active ? "resume_training" : "pause_training")) != null;

    public async Task<string> GrowAsync()
    {
        var res = await RequestAsync(Act("grow_brain"), 60000);
        return res is { } r ? Str(r, "message") : "";
    }

    public Task SaveCheckpointAsync() => RequestAsync(Act("save_checkpoint"), 60000);

    public async Task<MemoryGraphData> GetMemoryGraphAsync(int limitAni, int limitBilgi)
    {
        var res = await RequestAsync(new JsonObject { ["action"] = "graph", ["limit_ani"] = limitAni, ["limit_bilgi"] = limitBilgi }, 15000);
        if (res is { } r && r.TryGetProperty("data", out var d))
            return JsonSerializer.Deserialize<MemoryGraphData>(d.GetRawText()) ?? new();
        return new MemoryGraphData();
    }

    public async Task<(bool Ok, string Message)> FetchWikiTopicAsync(string topic)
    {
        var res = await RequestAsync(new JsonObject { ["action"] = "fetch_wiki_topic", ["topic"] = topic }, 20000);
        if (res is not { } r) return (false, L("Motor yanıt vermedi.", "The engine did not respond."));
        return Str(r, "status") == "ok" ? (true, Str(r, "summary")) : (false, Str(r, "message"));
    }

    public async Task<bool> BulkWikiIngestAsync(int limit, string lang)
    {
        var res = await RequestAsync(new JsonObject { ["action"] = "bulk_wiki_ingest", ["limit"] = limit, ["lang"] = lang });
        return res is { } r && Str(r, "status") == "started";
    }

    public async Task<string> ExportAsync(bool onnx)
    {
        var res = await RequestAsync(Act(onnx ? "export_onnx" : "export_package"), 180000);
        return res is { } r ? Str(r, "path") : "";
    }

    public void Stop()
    {
        _stopping = true;
        try
        {
            if (IsRunning)
            {
                // stdin kapanınca motor ağırlıkları kaydedip kendiliğinden çıkar
                try { _writer?.Close(); } catch (IOException) { }
                if (!_process!.WaitForExit(8000))
                    _process.Kill(entireProcessTree: true);
            }
        }
        catch (InvalidOperationException) { }
        finally
        {
            _process?.Dispose();
            _process = null;
            _writer = null;
        }
    }

    public void Dispose()
    {
        Stop();
        _writeLock.Dispose();
    }
}
