using System.Collections.ObjectModel;
using System.Speech.Synthesis;
using System.Speech.Recognition;
using System.Text.RegularExpressions;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Shapes;
using System.Windows.Threading;
using NovaApp.Models;
using NovaApp.Services;

namespace NovaApp;

public partial class MainWindow : Window
{
    private readonly BackendService _backend = new();
    private readonly ObservableCollection<ChatMessage> _messages = [];
    private readonly List<double> _lossHistory = [];
    private readonly DispatcherTimer _pollTimer = new();
    private readonly DispatcherTimer _clockTimer = new();

    private SpeechSynthesizer? _synth;
    private SpeechRecognitionEngine? _recognizer;
    private bool _voiceOutputEnabled = false;
    private bool _isListening = false;

    public MainWindow()
    {
        InitializeComponent();

        ChatItemsControl.ItemsSource = _messages;

        // Initialize TTS
        try
        {
            _synth = new SpeechSynthesizer();
            _synth.SetOutputToDefaultAudioDevice();
        }
        catch { }

        // Hook up backend events
        _backend.ReadyReceived += OnBackendReady;
        _backend.TelemetryReceived += OnTelemetryReceived;
        _backend.MessageReceived += OnMessageReceived;
        _backend.ConnectionStateChanged += OnConnectionStateChanged;
        _backend.ErrorReceived += OnErrorReceived;


        // Timers
        _pollTimer.Interval = TimeSpan.FromSeconds(1.5);
        _pollTimer.Tick += async (s, e) =>
        {
            if (_backend.IsRunning)
            {
                await _backend.RequestTelemetryAsync();
            }
        };

        _clockTimer.Interval = TimeSpan.FromSeconds(1.0);
        _clockTimer.Tick += (s, e) =>
        {
            TxtClock.Text = DateTime.Now.ToString("HH:mm:ss");
        };
        _clockTimer.Start();

        Loaded += async (s, e) =>
        {
            AddSystemMessage("🌟 Nova AGI Başlatılıyor... Python motoruna bağlanıyor.");
            bool started = await _backend.StartAsync("python");
            if (started)
            {
                _pollTimer.Start();
                try
                {
                    var cfg = await _backend.GetSettingsAsync();
                    ApplyLocalization(cfg.Language);
                    ApplyTheme(cfg.Theme);
                }
                catch { }
            }
        };

        Closed += (s, e) =>
        {
            _pollTimer.Stop();
            _clockTimer.Stop();
            _backend.Dispose();
        };
    }

    private void OnBackendReady(string version)
    {
        Dispatcher.Invoke(async () =>
        {
            try
            {
                var cfg = await _backend.GetSettingsAsync();
                ApplyLocalization(cfg.Language);
                ApplyTheme(cfg.Theme);
            }
            catch { }

            StatusDot.Fill = (Brush)FindResource("GpuGreenBrush");
            StatusText.Text = $"Motor Hazır v{version} (Sürekli Öğrenme Aktif)";
            TxtBottomStatus.Text = "✓ Nova Motoru Bağlandı.";
            AddSystemMessage($"✓ Nova AGI Motoru v{version} başarıyla bağlandı.");
        });
    }


    private void OnConnectionStateChanged(bool isConnected)
    {
        Dispatcher.Invoke(() =>
        {
            if (isConnected)
            {
                StatusDot.Fill = (Brush)FindResource("GpuGreenBrush");
                StatusText.Text = "Motor Çevrimiçi";
            }
            else
            {
                StatusDot.Fill = (Brush)FindResource("DangerBrush");
                StatusText.Text = "Motor Bağlantısı Kesildi";
                TxtBottomStatus.Text = "✗ Motor kapalı veya hata oluştu.";
            }
        });
    }

    private void OnErrorReceived(string error)
    {
        Dispatcher.Invoke(() =>
        {
            AddSystemMessage($"[Hata]: {error}");
        });
    }

    private void OnMessageReceived(string role, string text, string action)
    {
        Dispatcher.Invoke(() =>
        {
            _messages.Add(new ChatMessage
            {
                Role = role,
                Text = text,
                ActionText = action,
                Timestamp = DateTime.Now.ToString("HH:mm:ss")
            });
            ScrollChatToBottom();

            // Speech Synthesis (TTS)
            if (_voiceOutputEnabled && role.Equals("nova", StringComparison.OrdinalIgnoreCase) && _synth != null)
            {
                try
                {
                    _synth.SpeakAsyncCancelAll();
                    // Clean markdown asterisks and code blocks
                    string speechText = Regex.Replace(text, @"[*#`_~\[\]\(\)]", " ");
                    speechText = Regex.Replace(speechText, @"\s+", " ").Trim();
                    if (!string.IsNullOrWhiteSpace(speechText))
                    {
                        _synth.SpeakAsync(speechText);
                    }
                }
                catch { }
            }
        });
    }


    private void OnTelemetryReceived(TelemetryPacket packet)
    {
        Dispatcher.Invoke(() =>
        {
            // Loss & Step metrics
            TxtStep.Text = $"{packet.Step:N0}";
            TxtLoss.Text = packet.Loss > 0 ? packet.Loss.ToString("F4") : "—";
            TxtLr.Text = $"{packet.LearningRate:E2}";
            TxtVocab.Text = $"{packet.VocabSize:N0}";
            TxtEpisodic.Text = $"{packet.EpisodicNodes:N0}";
            TxtSemantic.Text = $"{packet.SemanticNodes:N0}";

            // Architecture params live
            if (packet.Architecture != null && packet.Architecture.Params > 0)
            {
                TxtParams.Text = $"{packet.Architecture.Params:N0} ({packet.Architecture.GrowthCount}x)";
            }
            else
            {
                TxtParams.Text = "689,408 (0x)";
            }

            // Web Server status
            if (packet.WebServer != null && packet.WebServer.IsRunning)
            {
                TxtWebStatus.Text = $"{packet.WebServer.LocalIp}:{packet.WebServer.Port}";
                TxtWebIcon.Text = "📱";
                BtnWebStatus.ToolTip = $"Mobil Web Sunucusu Aktif!\nTelefondan: http://{packet.WebServer.LocalIp}:{packet.WebServer.Port}\nBilgisayardan: http://localhost:{packet.WebServer.Port}";
            }
            else
            {
                TxtWebStatus.Text = "Mobil Web";
                TxtWebIcon.Text = "🌐";
                BtnWebStatus.ToolTip = "Mobil Web Sunucusu (Ayarlardan açabilirsiniz)";
            }



            // Loss history tracking for graph
            if (packet.Loss > 0 && !double.IsInfinity(packet.Loss))
            {
                _lossHistory.Add(packet.Loss);
                if (_lossHistory.Count > 80)
                {
                    _lossHistory.RemoveAt(0);
                }
                DrawLossCurve();
            }

            // Hardware & Multi-GPU updates
            var hw = packet.Hardware;
            var gpuSummary = hw.GpuSummary;

            if (gpuSummary.IsGpu)
            {
                if (gpuSummary.IsMultiGpu)
                {
                    GpuBadgeIcon.Text = "🔥";
                    GpuBadgeText.Text = $"{gpuSummary.Name} ({gpuSummary.VramStr})";
                    GpuBadgeBorder.Background = new SolidColorBrush(Color.FromArgb(0x33, 0xFF, 0x6B, 0x6B));
                    GpuBadgeBorder.BorderBrush = new SolidColorBrush(Color.FromArgb(0x88, 0xFF, 0x8E, 0x53));
                    GpuBadgeText.Foreground = new SolidColorBrush(Color.FromRgb(0xFF, 0x9B, 0x71));
                    TxtGpuHeader.Text = $"ÇOKLU GPU ({gpuSummary.Count}x Aygıt)";
                }
                else if (gpuSummary.Backend.Equals("DirectML", StringComparison.OrdinalIgnoreCase))
                {
                    GpuBadgeIcon.Text = "⚡";
                    GpuBadgeText.Text = $"{gpuSummary.Name} (DirectML)";
                    GpuBadgeBorder.Background = new SolidColorBrush(Color.FromArgb(0x33, 0x00, 0xE5, 0xB3));
                    GpuBadgeBorder.BorderBrush = new SolidColorBrush(Color.FromArgb(0x88, 0x00, 0xE5, 0xB3));
                    GpuBadgeText.Foreground = (Brush)FindResource("AccentCyanBrush");
                    TxtGpuHeader.Text = "GPU VRAM (DirectML)";
                }
                else
                {
                    GpuBadgeIcon.Text = "🔥";
                    GpuBadgeText.Text = $"{gpuSummary.Name} ({gpuSummary.VramStr})";
                    GpuBadgeBorder.Background = new SolidColorBrush(Color.FromArgb(0x33, 0x00, 0xD2, 0x6A));
                    GpuBadgeBorder.BorderBrush = new SolidColorBrush(Color.FromArgb(0x88, 0x00, 0xD2, 0x6A));
                    GpuBadgeText.Foreground = (Brush)FindResource("GpuGreenBrush");
                    TxtGpuHeader.Text = "GPU VRAM";
                }
            }
            else
            {
                GpuBadgeIcon.Text = "💻";
                GpuBadgeText.Text = $"{hw.Cpu.ShortName} ({hw.Cpu.Threads}T)";
                GpuBadgeBorder.Background = new SolidColorBrush(Color.FromArgb(0x33, 0xF5, 0x9E, 0x0B));
                GpuBadgeBorder.BorderBrush = new SolidColorBrush(Color.FromArgb(0x88, 0xF5, 0x9E, 0x0B));
                GpuBadgeText.Foreground = (Brush)FindResource("CpuAmberBrush");
                TxtGpuHeader.Text = "CPU Hızlandırma Modu";
            }

            // VRAM Bar calculation
            if (gpuSummary.VramMb > 0)
            {
                int totalVram = gpuSummary.VramMb;
                int allocated = hw.Gpus.Sum(g => g.VramAllocatedMb);
                double pct = totalVram > 0 ? (allocated * 100.0) / totalVram : 0;
                PbVram.Value = Math.Min(100, Math.Max(0, pct));
                TxtVramNumbers.Text = $"{allocated:N0} / {totalVram:N0} MB ({pct:F1}%)";
            }
            else
            {
                PbVram.Value = gpuSummary.IsGpu ? 100 : 0;
                TxtVramNumbers.Text = gpuSummary.IsGpu ? gpuSummary.VramStr : "GPU Yok (CPU Modu)";
            }

            // Multi-GPU items
            GpuDevicesItemsControl.ItemsSource = hw.Gpus;

            // System Summary Text
            TxtSystemSummary.Text = hw.SystemSummary;

            // Bottom Status
            TxtBottomStatus.Text = $"Adım: {packet.Step:N0} | Vocab: {packet.VocabSize} | Nodes: {packet.EpisodicNodes + packet.SemanticNodes} | {(packet.IsTraining ? "🔥 Eğitim Aktif" : "⏸ Beklemede")}";
        });
    }

    private void AddSystemMessage(string text)
    {
        _messages.Add(new ChatMessage
        {
            Role = "system",
            Text = text,
            Timestamp = DateTime.Now.ToString("HH:mm:ss")
        });
        ScrollChatToBottom();
    }

    private void ScrollChatToBottom()
    {
        ChatScrollViewer?.ScrollToEnd();
    }

    private async void BtnSend_Click(object sender, RoutedEventArgs e)
    {
        await SendCurrentPrompt();
    }

    private async void TxtInput_KeyDown(object sender, KeyEventArgs e)
    {
        if (e.Key == Key.Enter && !Keyboard.Modifiers.HasFlag(ModifierKeys.Shift))
        {
            e.Handled = true;
            await SendCurrentPrompt();
        }
    }

    private async Task SendCurrentPrompt()
    {
        var text = TxtInput.Text.Trim();
        if (string.IsNullOrWhiteSpace(text)) return;

        TxtInput.Clear();

        _messages.Add(new ChatMessage
        {
            Role = "user",
            Text = text,
            Timestamp = DateTime.Now.ToString("HH:mm:ss")
        });
        ScrollChatToBottom();

        if (text.StartsWith("!"))
        {
            await _backend.SendCommandAsync(text);
        }
        else
        {
            await _backend.SendMessageAsync(text);
        }
    }

    private async void QuickCommand_Click(object sender, RoutedEventArgs e)
    {
        if (sender is Button btn && btn.Tag is string cmd)
        {
            _messages.Add(new ChatMessage
            {
                Role = "user",
                Text = cmd,
                Timestamp = DateTime.Now.ToString("HH:mm:ss")
            });
            ScrollChatToBottom();
            await _backend.SendCommandAsync(cmd);
        }
    }

    private void BtnClearChat_Click(object sender, RoutedEventArgs e)
    {
        _messages.Clear();
        AddSystemMessage("Sohbet geçmişi ekranı temizlendi.");
    }

    private async void BtnSaveWeights_Click(object sender, RoutedEventArgs e)
    {
        await _backend.SaveCheckpointAsync();
        AddSystemMessage("✓ Ağırlık kaydetme isteği motora gönderildi.");
    }

    private async void BtnTriggerGrowth_Click(object sender, RoutedEventArgs e)
    {
        await _backend.TriggerGrowthAsync();
        AddSystemMessage("🧠 Sinir ağı büyüme komutu tetiklendi.");
    }

    private async void BtnOpenSettings_Click(object sender, RoutedEventArgs e)
    {
        var settingsWin = new SettingsWindow(_backend)
        {
            Owner = this
        };
        if (settingsWin.ShowDialog() == true)
        {
            try
            {
                var cfg = await _backend.GetSettingsAsync();
                ApplyLocalization(cfg.Language);
                ApplyTheme(cfg.Theme);
                AddSystemMessage(cfg.Language == "en" 
                    ? "✓ Settings successfully applied (Language: English, Live Engine Hyperparameters Updated)." 
                    : "✓ Ayarlar başarıyla uygulandı (Dil: Türkçe, Canlı Hiperparametreler Güncellendi).");
            }
            catch { }
        }
    }

    public void ApplyLocalization(string lang)
    {
        bool isEn = lang.Equals("en", StringComparison.OrdinalIgnoreCase);

        // Header & Subtitles
        TxtSubtitle.Text = isEn 
            ? "Autonomous Growing Neural Network & Consciousness Loop" 
            : "Otonom Büyüyen Sinir Ağı & Bilinç Döngüsü";
        TxtBtnGraph.Text = isEn ? "Memory Graph" : "Hafıza Grafiği";
        TxtBtnSave.Text = isEn ? "Save" : "Kaydet";
        TxtBtnGrow.Text = isEn ? "Grow" : "Büyüt";
        TxtBtnSettings.Text = isEn ? "Settings" : "Ayarlar";

        // Quick Command Chips
        TxtQuickCmds.Text = isEn ? "Quick Commands:" : "Hızlı Komutlar:";
        BtnChipStats.Content = isEn ? "🧠 !stats" : "🧠 !istatistik";
        BtnChipMemories.Content = isEn ? "📜 !memories" : "📜 !anilar";
        BtnChipHelp.Content = isEn ? "❓ !help" : "❓ !yardim";
        BtnChipClear.Content = isEn ? "🧹 Clear" : "🧹 Temizle";

        // Chat Input & Voice
        TxtBtnSend.Text = isEn ? "Send" : "Gönder";
        BtnVoiceOutput.ToolTip = isEn ? "Voice Output (TTS)" : "Sesli Yanıtı Aç / Kapat (Metin Okuma TTS)";
        BtnMic.ToolTip = isEn ? "Dictate / Mic (STT)" : "Sesle Konuş / Yazdır (Mikrofon)";

        // Sidebars
        TxtSecHardware.Text = isEn ? "⚡ HARDWARE & ACCELERATOR" : "⚡ DONANIM & HIZLANDIRICI";
        TxtSecLoss.Text = isEn ? "📉 REAL-TIME LOSS CURVE" : "📉 ANLIK LOSS EĞRİSİ";
        TxtSecMetrics.Text = isEn ? "🧠 NEURAL NETWORK METRICS" : "🧠 SİNİR AĞI METRİKLERİ";
        TxtSecSys.Text = isEn ? "💻 SYSTEM SPECS" : "💻 SİSTEM BİLGİSİ";

        // Metric Labels
        TxtLblStep.Text = isEn ? "Training Step" : "Eğitim Adımı";
        TxtLblLoss.Text = isEn ? "Real-time Loss" : "Anlık Loss";
        TxtLblLr.Text = isEn ? "Learning Rate" : "Öğrenme Hızı";
        TxtLblParams.Text = isEn ? "Neural Net Size" : "Sinir Ağı Boyutu";
        TxtLblVocab.Text = isEn ? "Vocab Size" : "Vocab Boyutu";
        TxtLblEpisodic.Text = isEn ? "Episodic Nodes (Memories)" : "Epizodik Node (Anı)";
        TxtLblSemantic.Text = isEn ? "Semantic Nodes (Facts)" : "Semantik Node (Bilgi)";


        // Status bar
        if (StatusText.Text.Contains("Motor Hazır") || StatusText.Text.Contains("Engine Ready"))
        {
            StatusText.Text = isEn ? "Engine Ready (Continuous Learning Active)" : "Motor Hazır (Sürekli Öğrenme Aktif)";
        }
    }

    public void ApplyTheme(string theme)
    {
        if (string.IsNullOrEmpty(theme)) return;
        if (theme.Contains("OLED"))
        {
            Background = new SolidColorBrush(Color.FromRgb(0x05, 0x07, 0x0B));
        }
        else if (theme.Contains("Mint"))
        {
            Background = new SolidColorBrush(Color.FromRgb(0x0A, 0x12, 0x14));
        }
        else
        {
            Background = (Brush)FindResource("BgDarkBrush");
        }
    }


    private async void BtnWebStatus_Click(object sender, RoutedEventArgs e)
    {
        var settingsWin = new SettingsWindow(_backend)
        {
            Owner = this
        };
        settingsWin.TabBtnWeb.IsChecked = true;
        if (settingsWin.ShowDialog() == true)
        {
            try
            {
                var cfg = await _backend.GetSettingsAsync();
                ApplyLocalization(cfg.Language);
                ApplyTheme(cfg.Theme);
            }
            catch { }
        }
    }

    private void BtnOpenGraph_Click(object sender, RoutedEventArgs e)

    {
        var graphWin = new MemoryGraphWindow(_backend)
        {
            Owner = this
        };
        graphWin.Show();
    }


    private void BtnVoiceOutput_Click(object sender, RoutedEventArgs e)
    {
        _voiceOutputEnabled = !_voiceOutputEnabled;
        TxtVoiceIcon.Text = _voiceOutputEnabled ? "🔊" : "🔇";
        BtnVoiceOutput.ToolTip = _voiceOutputEnabled ? "Sesli Okuma (TTS): Açık" : "Sesli Okuma (TTS): Kapalı";

        if (!_voiceOutputEnabled)
        {
            _synth?.SpeakAsyncCancelAll();
        }
        else
        {
            try
            {
                _synth?.SpeakAsync("Sesli yanıt sistemi açıldı.");
            }
            catch { }
        }
    }

    private void BtnMic_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            if (_isListening)
            {
                _recognizer?.RecognizeAsyncStop();
                _isListening = false;
                TxtMicIcon.Text = "🎙️";
                BtnMic.Background = (Brush)FindResource("CardBrush");
                return;
            }

            if (_recognizer == null)
            {
                _recognizer = new SpeechRecognitionEngine();
                _recognizer.SetInputToDefaultAudioDevice();
                var dictGrammar = new DictationGrammar();
                _recognizer.LoadGrammar(dictGrammar);

                _recognizer.SpeechRecognized += (s, args) =>
                {
                    Dispatcher.Invoke(() =>
                    {
                        if (!string.IsNullOrWhiteSpace(args.Result.Text))
                        {
                            TxtInput.Text = (TxtInput.Text + " " + args.Result.Text).Trim();
                            TxtInput.CaretIndex = TxtInput.Text.Length;
                        }
                    });
                };

                _recognizer.RecognizeCompleted += (s, args) =>
                {
                    Dispatcher.Invoke(() =>
                    {
                        _isListening = false;
                        TxtMicIcon.Text = "🎙️";
                        BtnMic.Background = (Brush)FindResource("CardBrush");
                    });
                };
            }

            _recognizer.RecognizeAsync(RecognizeMode.Single);
            _isListening = true;
            TxtMicIcon.Text = "🔴";
            BtnMic.Background = new SolidColorBrush(Color.FromArgb(0x66, 0xEF, 0x44, 0x44));
            AddSystemMessage("🎙️ Dinleniyor... Lütfen konuşun.");
        }
        catch (Exception ex)
        {
            _isListening = false;
            TxtMicIcon.Text = "🎙️";
            AddSystemMessage($"Mikrofon başlatılamadı: {ex.Message}. Windows Sesle Yazma kısayolunu (Win + H) kullanabilirsiniz.");
        }
    }


    private void LossCanvas_SizeChanged(object sender, SizeChangedEventArgs e)
    {
        DrawLossCurve();
    }

    private void DrawLossCurve()
    {
        LossCanvas.Children.Clear();
        if (_lossHistory.Count < 2)
        {
            TxtLossMin.Text = "min: —";
            TxtLossMax.Text = "max: —";
            return;
        }

        double width = LossCanvas.ActualWidth > 0 ? LossCanvas.ActualWidth : 280;
        double height = LossCanvas.ActualHeight > 0 ? LossCanvas.ActualHeight : 100;
        double pad = 6;

        double min = _lossHistory.Min();
        double max = _lossHistory.Max();
        if (Math.Abs(max - min) < 0.0001) max = min + 0.01;

        TxtLossMin.Text = $"min: {min:F3}";
        TxtLossMax.Text = $"max: {max:F3}";

        // Draw grid lines
        for (int i = 0; i <= 2; i++)
        {
            double y = pad + (height - 2 * pad) * i / 2.0;
            var line = new Line
            {
                X1 = pad,
                X2 = width - pad,
                Y1 = y,
                Y2 = y,
                Stroke = (Brush)FindResource("BorderBrush"),
                StrokeThickness = 1,
                StrokeDashArray = [2, 3]
            };
            LossCanvas.Children.Add(line);
        }

        // Draw path
        var geometry = new StreamGeometry();
        using (var ctx = geometry.Open())
        {
            for (int i = 0; i < _lossHistory.Count; i++)
            {
                double x = pad + (width - 2 * pad) * i / (_lossHistory.Count - 1);
                double y = height - pad - ((_lossHistory[i] - min) / (max - min)) * (height - 2 * pad);

                if (i == 0)
                    ctx.BeginFigure(new Point(x, y), false, false);
                else
                    ctx.LineTo(new Point(x, y), true, true);
            }
        }
        geometry.Freeze();

        var path = new Path
        {
            Data = geometry,
            Stroke = new SolidColorBrush(Color.FromRgb(0xFF, 0x6B, 0x6B)),
            StrokeThickness = 2
        };
        LossCanvas.Children.Add(path);

        // Draw last point dot
        if (_lossHistory.Count > 0)
        {
            double lastX = width - pad;
            double lastY = height - pad - ((_lossHistory[^1] - min) / (max - min)) * (height - 2 * pad);
            var dot = new Ellipse
            {
                Width = 6,
                Height = 6,
                Fill = new SolidColorBrush(Color.FromRgb(0xFF, 0x8E, 0x53)),
                Margin = new Thickness(lastX - 3, lastY - 3, 0, 0)
            };
            LossCanvas.Children.Add(dot);
        }
    }
}
