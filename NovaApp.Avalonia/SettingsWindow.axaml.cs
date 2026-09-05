using Avalonia.Controls;
using Avalonia.Interactivity;
using NovaApp.Models;
using NovaApp.Services;

namespace NovaApp.Avalonia;

public partial class SettingsWindow : Window
{
    private readonly BackendService _backend;
    private NovaSettings _settings = new();

    public bool WasSaved { get; private set; }

    public SettingsWindow() : this(new BackendService())
    {
    }

    public SettingsWindow(BackendService backend)
    {
        InitializeComponent();
        _backend = backend;
        Opened += async (_, _) => await LoadSettingsAsync();
    }

    private async Task LoadSettingsAsync()
    {
        _settings = await _backend.GetSettingsAsync();
        LanguageBox.SelectedIndex = _settings.Language.Equals("tr", StringComparison.OrdinalIgnoreCase) ? 1 : 0;
        TrainingBox.IsChecked = _settings.ContinuousTrainingEnabled;
        NeuralTrainingBox.IsChecked = _settings.ContinuousTrainingEnabled;
        WebBox.IsChecked = _settings.WebServerEnabled;
        PortBox.Value = _settings.WebServerPort;
        DeviceBox.SelectedIndex = _settings.Device switch
        {
            "cuda" => 1,
            "cpu" => 2,
            _ => 0
        };
        MultiGpuBox.IsChecked = _settings.MultiGpuEnabled;
        WorkersBox.Value = _settings.WorkerThreads;
        LearningRateBox.Text = _settings.LearningRate.ToString("G", System.Globalization.CultureInfo.InvariantCulture);
        BatchBox.Value = _settings.BatchSize;
        GrowthBox.Text = _settings.GrowthThreshold.ToString("G", System.Globalization.CultureInfo.InvariantCulture);
    }

    private void ShowSection(string title, string description) 
    {
        SectionTitle.Text = title;
        SectionDescription.Text = description;
        StatusText.Text = string.Empty;
    }

    private void SelectPanel(Control selected, string title, string description)
    {
        GeneralPanel.IsVisible = false;
        HardwarePanel.IsVisible = false;
        NeuralPanel.IsVisible = false;
        WebPanel.IsVisible = false;
        selected.IsVisible = true;
        ShowSection(title, description);
    }

    private void General_Click(object? sender, RoutedEventArgs e) => SelectPanel(GeneralPanel, "Genel Yapilandirma", "Dil ve temel sistem ayarlari.");
    private void Hardware_Click(object? sender, RoutedEventArgs e) => SelectPanel(HardwarePanel, "Donanim ve GPU", "Linux'ta CUDA, ROCm veya CPU modu kullanilir.");
    private void Neural_Click(object? sender, RoutedEventArgs e) => SelectPanel(NeuralPanel, "Sinir Agi ve Model", "Surekli egitim ve model davranisi.");
    private void Web_Click(object? sender, RoutedEventArgs e) => SelectPanel(WebPanel, "Mobil ve Web", "Yerel ag web sunucusu ayarlari.");

    private async void Save_Click(object? sender, RoutedEventArgs e)
    {
        var languageItem = LanguageBox.SelectedItem as ComboBoxItem;
        _settings.Language = languageItem?.Tag?.ToString() ?? "en";
        _settings.ContinuousTrainingEnabled = TrainingBox.IsChecked == true && NeuralTrainingBox.IsChecked == true;
        _settings.WebServerEnabled = WebBox.IsChecked == true;
        _settings.WebServerPort = (int)(PortBox.Value ?? 8080);
        var deviceItem = DeviceBox.SelectedItem as ComboBoxItem;
        _settings.Device = deviceItem?.Tag?.ToString() ?? "auto";
        _settings.MultiGpuEnabled = MultiGpuBox.IsChecked == true;
        _settings.WorkerThreads = (int)(WorkersBox.Value ?? 4);
        _settings.BatchSize = (int)(BatchBox.Value ?? 16);
        if (double.TryParse(LearningRateBox.Text, System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out var learningRate))
            _settings.LearningRate = learningRate;
        if (double.TryParse(GrowthBox.Text, System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out var growthThreshold))
            _settings.GrowthThreshold = growthThreshold;

        var saved = await _backend.SaveSettingsAsync(_settings);
        if (saved)
        {
            WasSaved = true;
            StatusText.Text = "Ayarlar kaydedildi ve Nova cekirdegine uygulandi.";
            Close(true);
        }
        else
        {
            StatusText.Text = "Ayarlar kaydedilemedi: Nova cekirdegi yanit vermedi.";
        }
    }

    private void Cancel_Click(object? sender, RoutedEventArgs e) => Close();
}
