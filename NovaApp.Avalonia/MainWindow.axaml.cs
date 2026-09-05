using System.Collections.ObjectModel;
using Avalonia.Controls;
using Avalonia.Input;
using Avalonia.Interactivity;
using Avalonia.Threading;
using NovaApp.Models;
using NovaApp.Services;

namespace NovaApp.Avalonia;

public partial class MainWindow : Window
{
    private readonly BackendService _backend = new();
    private readonly ObservableCollection<ChatMessage> _messages = [];
    private readonly DispatcherTimer _telemetryTimer = new() { Interval = TimeSpan.FromSeconds(1.5) };
    private readonly DispatcherTimer _clockTimer = new() { Interval = TimeSpan.FromSeconds(1) };
    private ChatMessage? _streamingMessage;
    private bool _isEnglish;

    public MainWindow()
    {
        InitializeComponent();
        ChatItems.ItemsSource = _messages;

        _backend.ReadyReceived += version => Dispatcher.UIThread.Post(() =>
        {
            StatusText.Text = $"Motor hazir v{version}";
            BottomStatus.Text = "Nova motoru baglandi.";
            AddMessage("system", "Nova AGI motoru basariyla baglandi.");
        });
        _backend.ConnectionStateChanged += connected => Dispatcher.UIThread.Post(() =>
        {
            StatusText.Text = connected ? "Motor cevrimici" : "Motor baglantisi kesildi";
            BottomStatus.Text = connected ? "Nova motoru baglandi." : "Nova motoru kapali veya hata olustu.";
        });
        _backend.ErrorReceived += error => Dispatcher.UIThread.Post(() => AddMessage("system", $"[Hata] {error}"));
        _backend.MessageReceived += (role, text, action) => Dispatcher.UIThread.Post(() =>
        {
            if (_streamingMessage != null)
            {
                _streamingMessage.Text = text;
                _streamingMessage = null;
                return;
            }

            AddMessage(role, text);
        });
        _backend.ChunkReceived += (role, chunk, done, finalReply) => Dispatcher.UIThread.Post(() =>
        {
            if (!done)
            {
                if (_streamingMessage == null)
                {
                    _streamingMessage = new ChatMessage { Role = role, Text = chunk };
                    _messages.Add(_streamingMessage);
                }
                else
                {
                    _streamingMessage.Text += chunk;
                }
            }
            else if (_streamingMessage != null)
            {
                if (!string.IsNullOrWhiteSpace(finalReply))
                    _streamingMessage.Text = finalReply;
                _streamingMessage = null;
            }

            ChatScroll.ScrollToEnd();
        });
        _backend.TelemetryReceived += packet => Dispatcher.UIThread.Post(() => ApplyTelemetry(packet));

        _telemetryTimer.Tick += async (_, _) =>
        {
            if (_backend.IsRunning)
                await _backend.RequestTelemetryAsync();
        };
        _clockTimer.Tick += (_, _) => ClockText.Text = DateTime.Now.ToString("HH:mm:ss");

        Opened += async (_, _) => await StartBackendAsync();
        Closed += (_, _) =>
        {
            _telemetryTimer.Stop();
            _clockTimer.Stop();
            _backend.Dispose();
        };
    }

    private async Task StartBackendAsync()
    {
        StatusText.Text = "Nova AGI beyni baslatiliyor...";
        BottomStatus.Text = "Nova cekirdegi yukleniyor...";
        AddMessage("system", "Nova AGI beyni baslatiliyor ve cekirdek servise baglaniliyor.");
        var started = await _backend.StartAsync("python");
        if (!started)
        {
            StatusText.Text = "Nova AGI beyni baglanamadi";
            BottomStatus.Text = "Nova cekirdegi baslatilamadi. Hata ayrintisi yukarida.";
            AddMessage("system", "Nova AGI cekirdegi baslatilamadi. Python bridge ve model loglarini kontrol edin.");
            return;
        }

        _clockTimer.Start();
        _telemetryTimer.Start();
        var history = await _backend.GetHistoryAsync(40);
        foreach (var message in history)
            _messages.Add(message);
        ChatScroll.ScrollToEnd();
    }

    private void ApplyTelemetry(TelemetryPacket packet)
    {
        StepText.Text = packet.Step.ToString("N0");
        LossText.Text = packet.Loss > 0 ? packet.Loss.ToString("F4") : "-";
        LearningRateText.Text = packet.LearningRate.ToString("E2");
        VocabText.Text = packet.VocabSize.ToString("N0");
        EpisodicText.Text = packet.EpisodicNodes.ToString("N0");
        SemanticText.Text = packet.SemanticNodes.ToString("N0");
        ParamsText.Text = packet.Architecture.Params > 0
            ? $"{packet.Architecture.Params:N0} ({packet.Architecture.GrowthCount}x)"
            : "-";

        var gpu = packet.Hardware.GpuSummary;
        GpuBadgeText.Text = gpu.IsGpu
            ? $"{gpu.Name} ({gpu.VramStr})"
            : $"{packet.Hardware.Cpu.ShortName} ({packet.Hardware.Cpu.Threads}T)";
        VramText.Text = gpu.VramMb > 0 ? $"{gpu.VramStr}" : "CPU modu";
        VramBar.Value = gpu.VramMb > 0 ? 35 : 0;
        GpuDevicesText.Text = string.Join(Environment.NewLine, packet.Hardware.Gpus.Select(g => $"{g.Name} - {g.VramStr}"));
        SystemText.Text = packet.Hardware.SystemSummary;
        BottomStatus.Text = $"Adim: {packet.Step:N0} | Vocab: {packet.VocabSize:N0} | Node: {packet.EpisodicNodes + packet.SemanticNodes:N0}";
    }

    private void ApplySettings(NovaSettings settings)
    {
        _isEnglish = settings.Language.Equals("en", StringComparison.OrdinalIgnoreCase);
        StatusText.Text = _isEnglish ? "Nova AGI engine online" : "Nova AGI motoru cevrimici";
        GraphButton.Content = _isEnglish ? "Memory Graph" : "Hafiza Grafigi";
        SaveButton.Content = _isEnglish ? "Save" : "Kaydet";
        GrowButton.Content = _isEnglish ? "Grow" : "Buyut";
        SettingsButton.Content = _isEnglish ? "Settings" : "Ayarlar";
        BottomStatus.Text = _isEnglish
            ? $"Language: English | Training: {(settings.ContinuousTrainingEnabled ? "Active" : "Paused")}"
            : $"Dil: Turkce | Egitim: {(settings.ContinuousTrainingEnabled ? "Aktif" : "Duraklatildi")}";
    }

    private void AddMessage(string role, string text)
    {
        _messages.Add(new ChatMessage
        {
            Role = role,
            Text = text,
            Timestamp = DateTime.Now.ToString("HH:mm:ss")
        });
        ChatScroll.ScrollToEnd();
    }

    private async Task SendPromptAsync()
    {
        var text = PromptInput.Text?.Trim();
        if (string.IsNullOrWhiteSpace(text))
            return;

        PromptInput.Text = string.Empty;
        AddMessage("user", text);
        if (text.StartsWith('!'))
            await _backend.SendCommandAsync(text);
        else
            await _backend.SendMessageAsync(text);
    }

    private async void Send_Click(object? sender, RoutedEventArgs e) => await SendPromptAsync();

    private async void Prompt_KeyDown(object? sender, KeyEventArgs e)
    {
        if (e.Key == Key.Enter && (e.KeyModifiers & KeyModifiers.Shift) == 0)
        {
            e.Handled = true;
            await SendPromptAsync();
        }
    }

    private async void Stats_Click(object? sender, RoutedEventArgs e)
    {
        AddMessage("user", "!istatistik");
        await _backend.SendCommandAsync("!istatistik");
    }

    private async void Memories_Click(object? sender, RoutedEventArgs e)
    {
        AddMessage("user", "!anilar 5");
        await _backend.SendCommandAsync("!anilar 5");
    }

    private async void Help_Click(object? sender, RoutedEventArgs e)
    {
        AddMessage("user", "!yardim");
        await _backend.SendCommandAsync("!yardim");
    }

    private void Clear_Click(object? sender, RoutedEventArgs e) => _messages.Clear();

    private async void Save_Click(object? sender, RoutedEventArgs e)
    {
        await _backend.SaveCheckpointAsync();
        AddMessage("system", "Agirlik kaydetme istegi motora gonderildi.");
    }

    private async void Grow_Click(object? sender, RoutedEventArgs e)
    {
        await _backend.TriggerGrowthAsync();
        AddMessage("system", "Sinir agi buyume komutu tetiklendi.");
    }

    private async void Voice_Click(object? sender, RoutedEventArgs e)
    {
        await _backend.ReadHistoryAsync(3);
        AddMessage("system", "Son sohbet gecmisi sesli okunuyor.");
    }

    private async void Mic_Click(object? sender, RoutedEventArgs e)
    {
        AddMessage("system", "Mikrofon dinleniyor...");
        var text = await _backend.ListenAsync(7);
        if (!string.IsNullOrWhiteSpace(text))
            PromptInput.Text = text;
        else
            AddMessage("system", "Ses algilanamadi.");
    }

    private async void OpenGraph_Click(object? sender, RoutedEventArgs e)
    {
        var window = new MemoryGraphWindow(_backend);
        await window.ShowDialog(this);
    }

    private async void Settings_Click(object? sender, RoutedEventArgs e)
    {
        var window = new SettingsWindow(_backend);
        var saved = await window.ShowDialog<bool?>(this);
        if (saved == true)
        {
            var settings = await _backend.GetSettingsAsync();
            ApplySettings(settings);
            AddMessage("system", _isEnglish
                ? "Settings saved and applied to the Nova engine."
                : "Ayarlar kaydedildi ve Nova cekirdegine uygulandi.");
        }
    }
}
