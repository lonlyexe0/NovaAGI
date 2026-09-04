using System.Diagnostics;
using System.IO;
using System.Text;
using System.Text.Json;
using NovaApp.Models;

namespace NovaApp.Services;

public class BackendService : IDisposable
{
    private Process? _process;
    private StreamWriter? _writer;
    private readonly CancellationTokenSource _cts = new();
    private bool _isDisposed;
    private int _requestId;

    private readonly Dictionary<int, TaskCompletionSource<JsonElement>> _pendingRequests = new();
    private readonly object _lock = new();

    public event Action<TelemetryPacket>? TelemetryReceived;
    public event Action<string, string, string>? MessageReceived;
    public event Action<string>? ReadyReceived;
    public event Action<string>? ErrorReceived;
    public event Action<bool>? ConnectionStateChanged;

    public bool IsRunning => _process != null && !_process.HasExited;

    public static string ResolvePythonPath(string? preference = null)
    {
        if (!string.IsNullOrEmpty(preference) && File.Exists(preference))
            return preference;

        var localApp = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
        var p310 = Path.Combine(localApp, @"Programs\Python\Python310\python.exe");
        if (File.Exists(p310)) return p310;

        var p311 = Path.Combine(localApp, @"Programs\Python\Python311\python.exe");
        if (File.Exists(p311)) return p311;

        var p312 = Path.Combine(localApp, @"Programs\Python\Python312\python.exe");
        if (File.Exists(p312)) return p312;

        return "python";
    }

    public static string ResolveBridgePath()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir != null)
        {
            var target = Path.Combine(dir.FullName, "nova_bridge.py");
            if (File.Exists(target)) return Path.GetFullPath(target);
            dir = dir.Parent;
        }

        if (File.Exists(@"c:\NOVA\nova_bridge.py"))
            return @"c:\NOVA\nova_bridge.py";

        return Path.GetFullPath("nova_bridge.py");
    }

    public async Task<bool> StartAsync(string? pythonExe = null)
    {
        try
        {
            var resolvedPython = ResolvePythonPath(pythonExe);
            var bridgePath = ResolveBridgePath();
            var workingDir = Path.GetDirectoryName(bridgePath) ?? Directory.GetCurrentDirectory();

            var startInfo = new ProcessStartInfo
            {
                FileName = resolvedPython,
                Arguments = $"\"{bridgePath}\"",
                WorkingDirectory = workingDir,
                RedirectStandardInput = true,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                UseShellExecute = false,
                CreateNoWindow = true,
                StandardOutputEncoding = Encoding.UTF8,
                StandardErrorEncoding = Encoding.UTF8
            };

            _process = new Process { StartInfo = startInfo, EnableRaisingEvents = true };
            _process.Exited += (s, e) =>
            {
                ConnectionStateChanged?.Invoke(false);
            };


            _process.Start();
            _writer = new StreamWriter(_process.StandardInput.BaseStream, new UTF8Encoding(false))
            {
                AutoFlush = true
            };

            // Read output loop
            _ = Task.Run(() => ReadOutputLoopAsync(_process.StandardOutput), _cts.Token);
            _ = Task.Run(() => ReadErrorLoopAsync(_process.StandardError), _cts.Token);

            ConnectionStateChanged?.Invoke(true);

            // Send initial ping
            await SendRawRequestAsync(new { action = "ping" });
            return true;
        }
        catch (Exception ex)
        {
            ErrorReceived?.Invoke($"Backend başlatılamadı: {ex.Message}");
            ConnectionStateChanged?.Invoke(false);
            return false;
        }
    }

    private async Task ReadOutputLoopAsync(StreamReader reader)
    {
        while (!_cts.IsCancellationRequested && _process != null && !_process.HasExited)
        {
            try
            {
                var line = await reader.ReadLineAsync(_cts.Token);
                if (line == null) break;
                line = line.Trim();
                if (string.IsNullOrEmpty(line)) continue;

                ProcessIncomingJson(line);
            }
            catch (OperationCanceledException)
            {
                break;
            }
            catch (Exception ex)
            {
                ErrorReceived?.Invoke($"Read loop error: {ex.Message}");
            }
        }
    }

    private async Task ReadErrorLoopAsync(StreamReader reader)
    {
        while (!_cts.IsCancellationRequested && _process != null && !_process.HasExited)
        {
            try
            {
                var line = await reader.ReadLineAsync(_cts.Token);
                if (line == null) break;
                if (!string.IsNullOrWhiteSpace(line))
                {
                    // Debug or warning from python
                    Debug.WriteLine($"[Python Error/Log] {line}");
                }
            }
            catch
            {
                break;
            }
        }
    }

    private void ProcessIncomingJson(string json)
    {
        try
        {
            using var doc = JsonDocument.Parse(json);
            var root = doc.RootElement;

            if (root.TryGetProperty("id", out var idProp) && idProp.ValueKind == JsonValueKind.Number)
            {
                var id = idProp.GetInt32();
                lock (_lock)
                {
                    if (_pendingRequests.TryGetValue(id, out var tcs))
                    {
                        tcs.TrySetResult(root.Clone());
                        _pendingRequests.Remove(id);
                    }
                }
            }

            if (!root.TryGetProperty("type", out var typeProp)) return;
            var type = typeProp.GetString();

            switch (type)
            {
                case "ready":
                    var ver = root.TryGetProperty("version", out var v) ? v.GetString() : "3.5";
                    ReadyReceived?.Invoke(ver ?? "3.5");
                    break;

                case "telemetry":
                    var packet = JsonSerializer.Deserialize<TelemetryPacket>(json);
                    if (packet != null)
                    {
                        TelemetryReceived?.Invoke(packet);
                    }
                    break;

                case "chat_reply":
                    var reply = root.TryGetProperty("reply", out var r) ? r.GetString() ?? "" : "";
                    var role = root.TryGetProperty("role", out var ro) ? ro.GetString() ?? "nova" : "nova";
                    var action = root.TryGetProperty("action", out var ac) ? ac.GetString() ?? "" : "";
                    MessageReceived?.Invoke(role, reply, action);
                    break;

                case "command_reply":
                    var cmdReply = root.TryGetProperty("reply", out var cr) ? cr.GetString() ?? "" : "";
                    MessageReceived?.Invoke("system", cmdReply, "");
                    break;

                case "error":
                    var errMsg = root.TryGetProperty("message", out var m) ? m.GetString() ?? "Bilinmeyen hata" : "Hata";
                    ErrorReceived?.Invoke(errMsg);
                    break;
            }
        }
        catch (Exception ex)
        {
            Debug.WriteLine($"JSON parse exception: {ex.Message} -> {json}");
        }
    }

    public async Task<JsonElement?> SendRawRequestAsync(object payload, int timeoutMs = 8000)
    {
        if (_writer == null || _process == null || _process.HasExited)
            return null;

        int id = Interlocked.Increment(ref _requestId);
        var tcs = new TaskCompletionSource<JsonElement>();

        lock (_lock)
        {
            _pendingRequests[id] = tcs;
        }

        try
        {
            var dict = JsonSerializer.Deserialize<Dictionary<string, object>>(JsonSerializer.Serialize(payload)) ?? new();
            dict["id"] = id;

            var jsonLine = JsonSerializer.Serialize(dict);
            await _writer.WriteLineAsync(jsonLine);

            using var ctsTimeout = new CancellationTokenSource(timeoutMs);
            ctsTimeout.Token.Register(() => tcs.TrySetCanceled());

            return await tcs.Task;
        }
        catch
        {
            lock (_lock)
            {
                _pendingRequests.Remove(id);
            }
            return null;
        }
    }

    public async Task SendMessageAsync(string prompt)
    {
        if (_writer == null) return;
        var json = JsonSerializer.Serialize(new { action = "chat", prompt });
        await _writer.WriteLineAsync(json);
    }

    public async Task SendCommandAsync(string command)
    {
        if (_writer == null) return;
        var json = JsonSerializer.Serialize(new { action = "command", command });
        await _writer.WriteLineAsync(json);
    }

    public async Task RequestTelemetryAsync()
    {
        if (_writer == null) return;
        var json = JsonSerializer.Serialize(new { action = "telemetry" });
        await _writer.WriteLineAsync(json);
    }

    public async Task<List<ChatMessage>> GetHistoryAsync(int limit = 40)
    {
        var res = await SendRawRequestAsync(new { action = "get_history", limit }, timeoutMs: 8000);
        var list = new List<ChatMessage>();
        if (res.HasValue && res.Value.TryGetProperty("messages", out var mProp) && mProp.ValueKind == JsonValueKind.Array)
        {
            foreach (var item in mProp.EnumerateArray())
            {
                var role = item.TryGetProperty("rol", out var r) ? r.GetString() ?? "nova" : "nova";
                var content = item.TryGetProperty("icerik", out var c) ? c.GetString() ?? "" : "";
                var zaman = item.TryGetProperty("zaman", out var z) ? z.GetString() ?? "" : "";

                bool isUser = role.Equals("kullanici", StringComparison.OrdinalIgnoreCase) || role.Equals("user", StringComparison.OrdinalIgnoreCase);
                bool isNova = role.Equals("nova", StringComparison.OrdinalIgnoreCase);
                bool isSystem = role.Equals("sistem", StringComparison.OrdinalIgnoreCase) || role.Equals("system", StringComparison.OrdinalIgnoreCase);

                list.Add(new ChatMessage
                {
                    Role = role,
                    Text = content,
                    Timestamp = zaman
                });
            }
        }
        return list;
    }

    public async Task ReadHistoryAsync(int count = 3)
    {
        await SendRawRequestAsync(new { action = "read_history", count });
    }

    public async Task SpeakAsync(string text)
    {
        if (string.IsNullOrWhiteSpace(text)) return;
        await SendRawRequestAsync(new { action = "speak", text });
    }

    public async Task<string> ObserveScreenAsync(string prompt = "", bool speak = true)
    {
        var res = await SendRawRequestAsync(new { action = "observe_screen", prompt, speak }, timeoutMs: 15000);
        if (res.HasValue && res.Value.TryGetProperty("text", out var tProp))
        {
            return tProp.GetString() ?? "";
        }
        return string.Empty;
    }

    public async Task<NovaSettings> GetSettingsAsync()
    {
        var res = await SendRawRequestAsync(new { action = "get_settings" });
        if (res.HasValue && res.Value.TryGetProperty("settings", out var sProp))
        {
            return JsonSerializer.Deserialize<NovaSettings>(sProp.GetRawText()) ?? new();
        }
        return new NovaSettings();
    }

    public async Task SaveSettingsAsync(NovaSettings settings)
    {
        await SendRawRequestAsync(new { action = "save_settings", settings });
    }

    public async Task<bool> PauseTrainingAsync()
    {
        var res = await SendRawRequestAsync(new { action = "pause_training" });
        return res.HasValue;
    }

    public async Task<bool> ResumeTrainingAsync()
    {
        var res = await SendRawRequestAsync(new { action = "resume_training" });
        return res.HasValue;
    }

    public async Task TriggerGrowthAsync()
    {
        await SendRawRequestAsync(new { action = "grow_brain" });
    }

    public async Task SaveCheckpointAsync()
    {
        await SendRawRequestAsync(new { action = "save_checkpoint" });
    }

    public async Task<MemoryGraphData> GetMemoryGraphAsync(int limitAni = 100, int limitBilgi = 250)
    {
        var res = await SendRawRequestAsync(new { action = "graph", limit_ani = limitAni, limit_bilgi = limitBilgi }, timeoutMs: 6000);
        if (res.HasValue && res.Value.TryGetProperty("data", out var dProp))
        {
            return JsonSerializer.Deserialize<MemoryGraphData>(dProp.GetRawText()) ?? new();
        }
        return new MemoryGraphData();
    }

    public async Task<(bool Success, string Message)> FetchWikiTopicAsync(string topic, string? lang = null)
    {
        var res = await SendRawRequestAsync(new { action = "fetch_wiki_topic", topic, lang }, timeoutMs: 12000);
        if (res.HasValue)
        {
            var status = res.Value.TryGetProperty("status", out var sProp) ? sProp.GetString() : "error";
            if (status == "ok")
            {
                var summary = res.Value.TryGetProperty("summary", out var smProp) ? smProp.GetString() ?? "" : "";
                return (true, summary);
            }
            var msg = res.Value.TryGetProperty("message", out var mProp) ? mProp.GetString() ?? "Bulunamadı" : "Hata";
            return (false, msg);
        }
        return (false, "Sunucudan yanıt alınamadı.");
    }

    public async Task<bool> BulkWikiIngestAsync(int limit = 500, string? lang = null)
    {
        var res = await SendRawRequestAsync(new { action = "bulk_wiki_ingest", limit, lang }, timeoutMs: 8000);
        if (res.HasValue && res.Value.TryGetProperty("status", out var sProp))
        {
            return sProp.GetString() == "started";
        }
        return false;
    }

    public async Task<string> ExportOnnxAsync()
    {
        var res = await SendRawRequestAsync(new { action = "export_onnx" }, timeoutMs: 15000);
        if (res.HasValue && res.Value.TryGetProperty("path", out var pProp))
        {
            return pProp.GetString() ?? "nova_model.onnx";
        }
        return string.Empty;
    }

    public async Task<string> ExportPackageAsync()
    {
        var res = await SendRawRequestAsync(new { action = "export_package" }, timeoutMs: 15000);
        if (res.HasValue && res.Value.TryGetProperty("path", out var pProp))
        {
            return pProp.GetString() ?? "nova_model_paketi.zip";
        }
        return string.Empty;
    }


    public void Stop()

    {
        try
        {
            _cts.Cancel();
            if (_writer != null)
            {
                try { _writer.WriteLine(JsonSerializer.Serialize(new { action = "exit" })); } catch { }
            }
            if (_process != null && !_process.HasExited)
            {
                _process.WaitForExit(1000);
                if (!_process.HasExited) _process.Kill();
            }
        }
        catch { }
        finally
        {
            _process = null;
            _writer = null;
            ConnectionStateChanged?.Invoke(false);
        }
    }

    public void Dispose()
    {
        if (_isDisposed) return;
        _isDisposed = true;
        Stop();
        _cts.Dispose();
    }
}
