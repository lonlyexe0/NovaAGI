using System.Diagnostics;
using System.Globalization;
using Avalonia.Controls;
using Avalonia.Interactivity;
using NovaApp.Models;
using NovaApp.Services;

namespace NovaApp;

public partial class SettingsWindow : Window
{
    private readonly BackendService _backend;
    private readonly bool _en;
    private NovaSettings _settings = new();
    private string _token = "";
    private readonly Control[] _panels;

    public bool RestartRequired { get; private set; }

    private string L(string tr, string en) => _en ? en : tr;

    // Avalonia önizleyicisi için
    public SettingsWindow() : this(new BackendService(), true, 0) { }

    public SettingsWindow(BackendService backend, bool en, int tab)
    {
        InitializeComponent();
        _backend = backend;
        _en = en;
        _panels = [PanelGeneral, PanelHardware, PanelNeural, PanelData, PanelWeb, PanelExport];
        Localize();
        Tabs.SelectedIndex = Math.Clamp(tab, 0, _panels.Length - 1);
        Opened += async (_, _) => await LoadAsync();
    }

    private void Localize()
    {
        Title = L("Nova AGI — Ayarlar", "Nova AGI — Settings");
        TxtTitle.Text = L("Ayarlar", "Settings");
        Tabs.ItemsSource = new[]
        {
            L("🌐  Genel", "🌐  General"), L("⚡  Donanım", "⚡  Hardware"), L("🧠  Sinir ağı", "🧠  Network"),
            L("📚  Veri & Merak", "📚  Data & curiosity"), L("📱  Mobil & Web", "📱  Mobile & web"), L("📦  Dışa aktar", "📦  Export"),
        };
        LblLanguage.Text = L("Arayüz ve veri dili", "Interface and data language");
        HintLanguage.Text = L("Wikipedia kaynakları, sesli yanıtlar ve komut çıktıları bu dili kullanır.",
                              "Wikipedia sources, voice replies and command output use this language.");
        LblDevice.Text = L("Hızlandırıcı", "Accelerator");
        DevAuto.Content = L("Otomatik (önerilen)", "Automatic (recommended)");
        DevCpu.Content = L("Yalnızca CPU", "CPU only");
        HintDevice.Text = L("Değişiklik uygulamayı yeniden başlatınca geçerli olur. AMD kartlar ROCm, Intel Arc kartlar XPU PyTorch derlemesi gerektirir (./install.sh otomatik seçer).",
                            "Takes effect after restarting the app. AMD cards need the ROCm build and Intel Arc the XPU build of PyTorch (./install.sh picks it).");
        ChkMultiGpu.Content = L("Birden fazla GPU varsa DataParallel ile dağıtık eğit", "Train with DataParallel when several GPUs are present");
        LblWorkers.Text = L("Veri hazırlama iş parçacıkları", "Data preparation workers");
        ChkTraining.Content = L("Sürekli arka plan eğitimi", "Continuous background training");
        HintTraining.Text = L("Yeni bilgi ve konuşmalarla modeli arka planda eğitir. Kapalıyken CPU/GPU boşta kalır.",
                              "Trains the model on new facts and conversations in the background. Off = idle CPU/GPU.");
        LblLr.Text = L("Öğrenme hızı", "Learning rate");
        LblBatch.Text = L("Batch boyutu", "Batch size");
        LblGrowth.Text = L("Büyüme plato eşiği", "Growth plateau threshold");
        LblBulk.Text = L("📚 Toplu Wikipedia içe aktar", "📚 Bulk Wikipedia import");
        HintBulk.Text = L("Hugging Face 'wikimedia/wikipedia' veri setinden makaleleri hafızaya akıtır ('datasets' paketi gerekir).",
                          "Streams articles from the Hugging Face 'wikimedia/wikipedia' dataset into memory (needs the 'datasets' package).");
        BtnBulk.Content = L("İndir", "Import");
        ChkCuriosity.Content = L("Otonom merak motoru (arka planda yeni konular keşfeder)", "Autonomous curiosity engine (explores new topics)");
        LblTopics.Text = L("Özel araştırma konuları (virgülle)", "Custom research topics (comma separated)");
        LblInterval.Text = L("Keşif aralığı", "Exploration interval");
        LblHf.Text = L("Hugging Face erişim anahtarı (isteğe bağlı)", "Hugging Face access token (optional)");
        ChkWeb.Content = L("Yerel ağ web sunucusunu aç", "Enable the local network web server");
        LblPhone.Text = L("Telefonla bağlan", "Connect from a phone");
        BtnCopyUrl.Content = L("📋 Kopyala", "📋 Copy");
        BtnOpenUrl.Content = L("🔗 Tarayıcıda aç", "🔗 Open in browser");
        HintWeb.Text = L("Adres erişim anahtarı içerir; yalnızca aynı Wi-Fi'deki güvendiğiniz cihazlarla paylaşın. İnternet üzerinden erişim için: ./nova.sh tunnel",
                         "The link contains the access key; share it only with trusted devices on your Wi-Fi. For access over the internet: ./nova.sh tunnel");
        HintOnnx.Text = L("TensorRT, OpenVINO, ONNX Runtime ve tarayıcılarda çalıştırmak için.", "Run with TensorRT, OpenVINO, ONNX Runtime or in browsers.");
        HintZip.Text = L("Ağırlıklar ve kelime haznesini tek dosyada paketler.", "Packs weights and vocabulary into one file.");
        BtnOnnx.Content = L("ONNX'e aktar", "Export ONNX");
        BtnZip.Content = L("ZIP oluştur", "Create ZIP");
        BtnCancel.Content = L("İptal", "Cancel");
        BtnSave.Content = L("Kaydet ve uygula", "Save & apply");
    }

    private async Task LoadAsync()
    {
        (_settings, _token) = await _backend.GetSettingsAsync();
        CmbLanguage.SelectedIndex = _settings.IsEnglish ? 0 : 1;
        CmbDevice.SelectedIndex = _settings.Device switch { "cuda" or "rocm" => 1, "xpu" => 2, "cpu" => 3, _ => 0 };
        ChkMultiGpu.IsChecked = _settings.MultiGpuEnabled;
        SliderWorkers.Value = Math.Clamp(_settings.WorkerThreads, 1, 16);
        ChkTraining.IsChecked = _settings.ContinuousTrainingEnabled;
        TxtLr.Text = _settings.LearningRate.ToString(CultureInfo.InvariantCulture);
        NumBatch.Value = _settings.BatchSize;
        TxtGrowth.Text = _settings.GrowthThreshold.ToString(CultureInfo.InvariantCulture);
        ChkCuriosity.IsChecked = _settings.CuriosityEnabled;
        TxtTopics.Text = _settings.CuriosityTopics;
        CmbInterval.SelectedIndex = _settings.CuriosityInterval switch { <= 10 => 0, <= 25 => 1, <= 50 => 2, _ => 3 };
        TxtHf.Text = _settings.HfToken;
        ChkWeb.IsChecked = _settings.WebServerEnabled;
        TxtPort.Text = (_settings.WebServerPort > 0 ? _settings.WebServerPort : 8080).ToString();
        UpdateUrl();
    }

    private void Tabs_SelectionChanged(object? sender, SelectionChangedEventArgs e)
    {
        if (_panels == null) return;
        for (var i = 0; i < _panels.Length; i++)
            _panels[i].IsVisible = i == Tabs.SelectedIndex;
    }

    private static string LocalIp()
    {
        try
        {
            using var s = new System.Net.Sockets.Socket(System.Net.Sockets.AddressFamily.InterNetwork,
                System.Net.Sockets.SocketType.Dgram, System.Net.Sockets.ProtocolType.Udp);
            s.Connect("10.254.254.254", 1);
            return (s.LocalEndPoint as System.Net.IPEndPoint)?.Address.ToString() ?? "127.0.0.1";
        }
        catch (System.Net.Sockets.SocketException) { return "127.0.0.1"; }
    }

    private int Port => int.TryParse(TxtPort.Text, out var p) && p is > 0 and < 65536 ? p : 8080;
    private string Url(string host) => $"http://{host}:{Port}/?token={_token}";

    private void UpdateUrl()
    {
        TxtUrl.Text = ChkWeb.IsChecked == true
            ? Url(LocalIp())
            : L("Önce web sunucusunu açıp kaydedin.", "Enable and save the web server first.");
    }

    private void Web_Changed(object? sender, RoutedEventArgs e)
    {
        if (IsLoaded) UpdateUrl();
    }

    private async void BtnCopyUrl_Click(object? sender, RoutedEventArgs e)
    {
        if (Clipboard != null && ChkWeb.IsChecked == true) await Clipboard.SetTextAsync(Url(LocalIp()));
    }

    private void BtnOpenUrl_Click(object? sender, RoutedEventArgs e)
    {
        try { Process.Start(new ProcessStartInfo("xdg-open", Url("localhost")) { UseShellExecute = false }); }
        catch (Exception ex) { TxtUrl.Text = ex.Message; }
    }

    private async void BtnBulk_Click(object? sender, RoutedEventArgs e)
    {
        var count = CmbBulk.SelectedItem is ComboBoxItem { Tag: string t } && int.TryParse(t, out var c) ? c : 500;
        BtnBulk.IsEnabled = false;
        var ok = await _backend.BulkWikiIngestAsync(count, CmbLanguage.SelectedIndex == 1 ? "tr" : "en");
        TxtBulkStatus.Text = ok
            ? L($"✓ {count:N0} makale arka planda hafızaya aktarılıyor.", $"✓ Importing {count:N0} articles in the background.")
            : L("✗ Başlatılamadı.", "✗ Could not start.");
        BtnBulk.IsEnabled = true;
    }

    private async void BtnExport_Click(object? sender, RoutedEventArgs e)
    {
        if (sender is not Button { Tag: string kind } btn) return;
        btn.IsEnabled = false;
        TxtExport.Text = L("⏳ Dışa aktarılıyor…", "⏳ Exporting…");
        var path = await _backend.ExportAsync(kind == "onnx");
        TxtExport.Text = string.IsNullOrEmpty(path) ? L("✗ Dışa aktarma başarısız.", "✗ Export failed.") : $"✓ {path}";
        btn.IsEnabled = true;
    }

    private async void BtnSave_Click(object? sender, RoutedEventArgs e)
    {
        _settings.Language = CmbLanguage.SelectedIndex == 1 ? "tr" : "en";
        _settings.Device = (CmbDevice.SelectedItem as ComboBoxItem)?.Tag as string ?? "auto";
        _settings.MultiGpuEnabled = ChkMultiGpu.IsChecked == true;
        _settings.WorkerThreads = (int)SliderWorkers.Value;
        _settings.ContinuousTrainingEnabled = ChkTraining.IsChecked == true;
        if (double.TryParse(TxtLr.Text, NumberStyles.Float, CultureInfo.InvariantCulture, out var lr) && lr > 0)
            _settings.LearningRate = lr;
        _settings.BatchSize = (int)(NumBatch.Value ?? _settings.BatchSize);
        if (double.TryParse(TxtGrowth.Text, NumberStyles.Float, CultureInfo.InvariantCulture, out var gt) && gt > 0)
            _settings.GrowthThreshold = gt;
        _settings.CuriosityEnabled = ChkCuriosity.IsChecked == true;
        _settings.CuriosityTopics = TxtTopics.Text?.Trim() ?? "";
        if (CmbInterval.SelectedItem is ComboBoxItem { Tag: string it } && int.TryParse(it, out var interval))
            _settings.CuriosityInterval = interval;
        _settings.HfToken = TxtHf.Text?.Trim() ?? "";
        _settings.WebServerEnabled = ChkWeb.IsChecked == true;
        _settings.WebServerPort = Port;

        BtnSave.IsEnabled = false;
        RestartRequired = await _backend.SaveSettingsAsync(_settings);
        Close(true);
    }

    private void BtnCancel_Click(object? sender, RoutedEventArgs e) => Close(false);
}
