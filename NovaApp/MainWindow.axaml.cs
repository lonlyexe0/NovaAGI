using System.Collections.ObjectModel;
using Avalonia;
using Avalonia.Controls;
using Avalonia.Input;
using Avalonia.Interactivity;
using Avalonia.Media;
using Avalonia.Threading;
using NovaApp.Models;
using NovaApp.Services;

namespace NovaApp;

public partial class MainWindow : Window
{
    private readonly BackendService _backend = new();
    private readonly ObservableCollection<ChatMessage> _messages = [];
    private readonly Dictionary<int, ChatMessage> _streams = [];
    private readonly DispatcherTimer _pollTimer = new() { Interval = TimeSpan.FromSeconds(1.5) };
    private readonly DispatcherTimer _clockTimer = new() { Interval = TimeSpan.FromSeconds(1) };

    private bool _en = !(Environment.GetEnvironmentVariable("LANG") ?? "").StartsWith("tr", StringComparison.OrdinalIgnoreCase);
    private bool _voiceOn = true;
    private bool _listening;
    private bool _training = true;
    private bool _ready;
    private string _engineVersion = "";

    private string L(string tr, string en) => _en ? en : tr;

    public MainWindow()
    {
        InitializeComponent();
        ChatList.ItemsSource = _messages;
        TxtInput.AddHandler(KeyDownEvent, TxtInput_KeyDown, RoutingStrategies.Tunnel);

        _backend.ReadyReceived += (v, d) => Dispatcher.UIThread.Post(() => OnReady(v, d));
        _backend.TelemetryReceived += p => Dispatcher.UIThread.Post(() => OnTelemetry(p));
        _backend.ChunkReceived += (id, c, done, reply, action) => Dispatcher.UIThread.Post(() => OnChunk(id, c, done, reply, action));
        _backend.ErrorReceived += e => Dispatcher.UIThread.Post(() => AddSystem("⚠️ " + e));
        _backend.ConnectionStateChanged += on => Dispatcher.UIThread.Post(() => SetStatus(on ? null : false));

        _pollTimer.Tick += async (_, _) => { if (_backend.IsRunning) await _backend.RequestTelemetryAsync(); };
        _clockTimer.Tick += (_, _) => TxtClock.Text = DateTime.Now.ToString("HH:mm:ss");
        _clockTimer.Start();

        ApplyLocalization();
        SetStatus(null);

        Opened += async (_, _) =>
        {
            AddSystem(L("Nova motoru başlatılıyor…", "Starting the Nova engine…"));
            if (await _backend.StartAsync()) _pollTimer.Start();
        };
        Closing += (_, _) =>
        {
            _pollTimer.Stop();
            _clockTimer.Stop();
            _backend.Dispose();
        };
    }

    // ── Motor olayları ────────────────────────────────────────────────────────
    private async void OnReady(string version, string device)
    {
        _ready = true;
        _engineVersion = version;
        SetStatus(true);
        try
        {
            var (settings, _) = await _backend.GetSettingsAsync();
            _en = settings.IsEnglish;
            ApplyLocalization();
            _training = settings.ContinuousTrainingEnabled;
        }
        catch (Exception) { /* varsayılan dil ile devam */ }

        _messages.Clear();
        var history = await _backend.GetHistoryAsync(40);
        foreach (var m in history) _messages.Add(m);
        AddSystem(L($"✓ Nova motoru bağlandı (v{version}, {device}).", $"✓ Nova engine connected (v{version}, {device})."));
        ScrollToEnd();
    }

    private void OnChunk(int id, string chunk, bool done, string reply, string? action)
    {
        if (!_streams.TryGetValue(id, out var msg))
        {
            msg = new ChatMessage { Role = "nova", IsStreaming = true };
            _streams[id] = msg;
            _messages.Add(msg);
        }
        if (!done)
        {
            msg.Text += chunk;
        }
        else
        {
            if (!string.IsNullOrEmpty(reply)) msg.Text = reply;
            msg.ActionText = action ?? "";
            msg.IsStreaming = false;
            _streams.Remove(id);
            if (_voiceOn && msg.IsNova) _ = _backend.SpeakAsync(msg.Text);
        }
        ScrollToEnd();
    }

    private void OnTelemetry(TelemetryPacket p)
    {
        TxtStep.Text = p.Step.ToString("N0");
        TxtLr.Text = p.LearningRate.ToString("0.00e+0");
        TxtParams.Text = p.Architecture.Params >= 1_000_000
            ? $"{p.Architecture.Params / 1e6:0.00}M"
            : $"{p.Architecture.Params / 1e3:0}K";
        TxtArch.Text = $"{p.Architecture.NLayers}×{p.Architecture.EmbedDim} · ff {p.Architecture.FfDim}";
        TxtEpisodic.Text = p.EpisodicNodes.ToString("N0");
        TxtSemantic.Text = p.SemanticNodes.ToString("N0");

        LossChart.Push(p.Loss);
        TxtLossNow.Text = p.Loss > 0 ? p.Loss.ToString("0.0000") : "—";
        TxtLossRange.Text = LossChart.Min is { } mn && LossChart.Max is { } mx ? $"{mn:0.000} – {mx:0.000}" : "";

        var hw = p.Hardware;
        var gpu = hw.GpuSummary;
        var (badge, color) = gpu.IsGpu
            ? ($"⚡ {gpu.ShortName} · {gpu.Backend}", gpu.IsMultiGpu ? "#FB923C" : "#34D399")
            : ($"💻 {hw.Cpu.ShortName} · {hw.Cpu.Threads}T", "#FBBF24");
        DeviceBadgeText.Text = badge;
        DeviceBadgeText.Foreground = new SolidColorBrush(Color.Parse(color));
        DeviceBadge.BorderBrush = new SolidColorBrush(Color.Parse(color), 0.45);

        TxtGpuName.Text = gpu.IsGpu ? gpu.Name : L("CPU modu", "CPU mode");
        var allocated = hw.Gpus.Sum(g => g.VramAllocatedMb);
        if (gpu.VramMb > 0)
        {
            var pct = allocated * 100.0 / gpu.VramMb;
            PbVram.Value = Math.Clamp(pct, 0, 100);
            TxtVram.Text = $"{allocated:N0} / {gpu.VramMb:N0} MB";
        }
        else
        {
            PbVram.Value = 0;
            TxtVram.Text = gpu.IsGpu ? gpu.VramStr : $"RAM {hw.Ram.FreeGb:0.#}/{hw.Ram.TotalGb:0.#} GB";
        }
        GpuList.ItemsSource = hw.Gpus.Where(g => g.IsGpu).ToList();
        TxtTier.Text = p.HardwareTier;
        TxtSystem.Text = hw.SystemSummary;

        var web = p.WebServer;
        TxtWeb.Text = web.IsRunning ? $"📱 {web.LocalIp}:{web.Port}" : "📱 Web";
        ToolTip.SetTip(BtnWeb, web.IsRunning
            ? L("Mobil erişim açık — bağlantı adresi için tıklayın", "Mobile access on — click for the link")
            : L("Mobil & web erişimi (kapalı)", "Mobile & web access (off)"));

        _training = p.IsTraining;
        UpdateTrainingChip();
        TxtBottom.Text = $"{L("Adım", "Step")} {p.Step:N0}  ·  {L("Düğüm", "Nodes")} {p.EpisodicNodes + p.SemanticNodes:N0}  ·  " +
                         $"{L("Kuyruk", "Queue")} {p.Untrained:N0}  ·  {p.Device}  ·  " +
                         (p.IsTraining ? L("🔥 Eğitim aktif", "🔥 Training") : L("⏸ Eğitim duraklatıldı", "⏸ Training paused"));
    }

    private void SetStatus(bool? online)
    {
        var (brush, text) = online switch
        {
            true => ("OkBrush", L($"Motor hazır · v{_engineVersion}", $"Engine ready · v{_engineVersion}")),
            false => ("DangerBrush", L("Motor bağlantısı yok", "Engine offline")),
            null => ("WarnBrush", L("Bağlanıyor…", "Connecting…")),
        };
        StatusDot.Fill = (IBrush)this.FindResource(brush)!;
        StatusText.Text = text;
        if (online == false) _ready = false;
    }

    // ── Sohbet ────────────────────────────────────────────────────────────────
    private void AddSystem(string text)
    {
        _messages.Add(new ChatMessage { Role = "system", Text = text });
        ScrollToEnd();
    }

    private void ScrollToEnd() => Dispatcher.UIThread.Post(() => ChatScroll.ScrollToEnd(), DispatcherPriority.Background);

    private async Task SendAsync(string text)
    {
        text = text.Trim();
        if (text.Length == 0) return;
        if (!_backend.IsRunning)
        {
            AddSystem(L("⚠️ Nova motoru çalışmıyor.", "⚠️ The Nova engine is not running."));
            return;
        }
        _messages.Add(new ChatMessage { Role = "user", Text = text });
        ScrollToEnd();
        var id = await _backend.SendChatAsync(text);
        if (id > 0 && !_streams.ContainsKey(id))
        {
            var placeholder = new ChatMessage { Role = text.StartsWith('!') ? "system" : "nova", IsStreaming = true };
            _streams[id] = placeholder;
            _messages.Add(placeholder);
            ScrollToEnd();
        }
    }

    private async void TxtInput_KeyDown(object? sender, KeyEventArgs e)
    {
        if (e.Key == Key.Enter && !e.KeyModifiers.HasFlag(KeyModifiers.Shift))
        {
            e.Handled = true;
            var text = TxtInput.Text ?? "";
            TxtInput.Text = "";
            await SendAsync(text);
        }
    }

    private async void BtnSend_Click(object? sender, RoutedEventArgs e)
    {
        var text = TxtInput.Text ?? "";
        TxtInput.Text = "";
        await SendAsync(text);
    }

    private void SpeakMessage_Click(object? sender, RoutedEventArgs e)
    {
        if (sender is Button { Tag: string text } && !string.IsNullOrWhiteSpace(text))
            _ = _backend.SpeakAsync(text);
    }

    // ── Hızlı eylemler ────────────────────────────────────────────────────────
    private Button? _trainingChip;

    private void BuildChips()
    {
        ChipsPanel.Children.Clear();
        void Chip(string label, Func<Task> action)
        {
            var b = new Button { Content = label, Classes = { "chip" } };
            b.Click += async (_, _) => await action();
            ChipsPanel.Children.Add(b);
        }
        Chip(L("👁 Ekranı izle", "👁 Watch screen"), WatchScreenAsync);
        Chip(L("🔊 Geçmişi oku", "🔊 Read history"), () => _backend.ReadHistoryAsync(3));
        Chip(L("☕ Brifing", "☕ Briefing"), () => SendAsync(L("!brifing", "!briefing")));
        Chip(L("📊 İstatistik", "📊 Stats"), () => SendAsync("!istatistik"));
        Chip(L("📜 Anılar", "📜 Memories"), () => SendAsync("!anilar 5"));
        Chip("🤗 HF", () => SendAsync("!hf"));
        Chip(L("❓ Yardım", "❓ Help"), () => SendAsync(L("!yardim", "!help")));
        Chip(L("🧹 Temizle", "🧹 Clear"), () => { _messages.Clear(); return Task.CompletedTask; });
        _trainingChip = new Button { Classes = { "chip" } };
        _trainingChip.Click += async (_, _) => await ToggleTrainingAsync();
        ChipsPanel.Children.Insert(2, _trainingChip);
        UpdateTrainingChip();
    }

    private void UpdateTrainingChip()
    {
        if (_trainingChip != null)
            _trainingChip.Content = _training ? L("⏸ Eğitimi durdur", "⏸ Pause training") : L("▶ Eğitimi başlat", "▶ Resume training");
    }

    private async Task ToggleTrainingAsync()
    {
        if (!_backend.IsRunning || _trainingChip == null) return;
        _trainingChip.IsEnabled = false;
        if (await _backend.SetTrainingAsync(!_training))
        {
            _training = !_training;
            AddSystem(_training ? L("▶ Sürekli eğitim devam ediyor.", "▶ Continuous training resumed.")
                                : L("⏸ Sürekli eğitim duraklatıldı.", "⏸ Continuous training paused."));
        }
        UpdateTrainingChip();
        _trainingChip.IsEnabled = true;
    }

    private async Task WatchScreenAsync()
    {
        if (!_backend.IsRunning) return;
        AddSystem(L("👁 Nova ekranı gözlemliyor…", "👁 Nova is observing the screen…"));
        var res = await _backend.ObserveScreenAsync(L("ekranımı izle", "watch my screen"), _voiceOn);
        if (!string.IsNullOrWhiteSpace(res))
        {
            _messages.Add(new ChatMessage { Role = "nova", Text = res, ActionText = L("Görsel gözlem", "Visual observation") });
            ScrollToEnd();
        }
    }

    private void BtnVoice_Click(object? sender, RoutedEventArgs e)
    {
        _voiceOn = !_voiceOn;
        BtnVoice.Content = _voiceOn ? "🔊" : "🔇";
        ToolTip.SetTip(BtnVoice, _voiceOn ? L("Sesli yanıt açık", "Voice replies on") : L("Sesli yanıt kapalı", "Voice replies off"));
        if (!_voiceOn) _ = _backend.StopSpeakingAsync();
    }

    private async void BtnMic_Click(object? sender, RoutedEventArgs e)
    {
        if (_listening || !_backend.IsRunning) return;
        _listening = true;
        BtnMic.Classes.Add("active");
        BtnMic.Content = "🔴";
        try
        {
            var text = await _backend.ListenAsync(7);
            if (!string.IsNullOrWhiteSpace(text))
            {
                TxtInput.Text = ((TxtInput.Text ?? "") + " " + text).Trim();
                TxtInput.CaretIndex = TxtInput.Text.Length;
                TxtInput.Focus();
            }
            else
            {
                AddSystem(L("ℹ️ Ses algılanamadı. Mikrofonu ve 'pyaudio' kurulumunu kontrol edin.",
                            "ℹ️ No speech detected. Check the microphone and the 'pyaudio' install."));
            }
        }
        finally
        {
            _listening = false;
            BtnMic.Classes.Remove("active");
            BtnMic.Content = "🎤";
        }
    }

    // ── Üst çubuk ─────────────────────────────────────────────────────────────
    private async void BtnSave_Click(object? sender, RoutedEventArgs e)
    {
        BtnSave.IsEnabled = false;
        await _backend.SaveCheckpointAsync();
        AddSystem(L("💾 Ağırlıklar kaydedildi.", "💾 Weights saved."));
        BtnSave.IsEnabled = true;
    }

    private async void BtnGrow_Click(object? sender, RoutedEventArgs e)
    {
        BtnGrow.IsEnabled = false;
        var msg = await _backend.GrowAsync();
        AddSystem("🧠 " + (string.IsNullOrEmpty(msg) ? L("Büyüme isteği gönderildi.", "Growth requested.") : msg));
        BtnGrow.IsEnabled = true;
    }

    private void BtnGraph_Click(object? sender, RoutedEventArgs e) =>
        new MemoryGraphWindow(_backend, _en).Show(this);

    private async void BtnSettings_Click(object? sender, RoutedEventArgs e) => await OpenSettingsAsync(0);
    private async void BtnWeb_Click(object? sender, RoutedEventArgs e) => await OpenSettingsAsync(4);

    private async Task OpenSettingsAsync(int tab)
    {
        if (!_ready)
        {
            AddSystem(L("⚠️ Ayarlar için motorun bağlanmasını bekleyin.", "⚠️ Wait for the engine to connect."));
            return;
        }
        var win = new SettingsWindow(_backend, _en, tab);
        if (await win.ShowDialog<bool>(this))
        {
            var (settings, _) = await _backend.GetSettingsAsync();
            _en = settings.IsEnglish;
            ApplyLocalization();
            AddSystem(win.RestartRequired
                ? L("✓ Ayarlar kaydedildi. Cihaz değişikliği için uygulamayı yeniden başlatın.", "✓ Settings saved. Restart the app to apply the device change.")
                : L("✓ Ayarlar uygulandı.", "✓ Settings applied."));
        }
    }

    private void ApplyLocalization()
    {
        _backend.English = _en;
        TxtSubtitle.Text = L("Kendi kendine büyüyen sinir ağı", "Self-growing neural network");
        BtnGraph.Content = L("🧠 Hafıza", "🧠 Memory");
        BtnSave.Content = L("💾 Kaydet", "💾 Save");
        BtnGrow.Content = L("⚡ Büyüt", "⚡ Grow");
        BtnSettings.Content = L("⚙ Ayarlar", "⚙ Settings");
        TxtInput.Watermark = L("Nova'ya yazın… (Shift+Enter: yeni satır)", "Message Nova… (Shift+Enter: new line)");
        ToolTip.SetTip(BtnMic, L("Sesle yaz", "Dictate"));
        ToolTip.SetTip(BtnVoice, _voiceOn ? L("Sesli yanıt açık", "Voice replies on") : L("Sesli yanıt kapalı", "Voice replies off"));
        ToolTip.SetTip(BtnSave, L("Model ağırlıklarını kaydet", "Save model weights"));
        ToolTip.SetTip(BtnGrow, L("Sinir ağını elle büyüt", "Grow the network manually"));
        SecHardware.Text = L("HIZLANDIRICI", "ACCELERATOR");
        SecLoss.Text = L("LOSS", "LOSS");
        SecMetrics.Text = L("SİNİR AĞI", "NETWORK");
        SecSystem.Text = L("SİSTEM", "SYSTEM");
        LblStep.Text = L("Eğitim adımı", "Training step");
        LblParams.Text = L("Parametre", "Parameters");
        LblLr.Text = L("Öğrenme hızı", "Learning rate");
        LblArch.Text = L("Mimari", "Architecture");
        LblEpisodic.Text = L("Anılar", "Memories");
        LblSemantic.Text = L("Bilgiler", "Facts");
        SetStatus(_ready ? true : null);
        BuildChips();
    }
}
