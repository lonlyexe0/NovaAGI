using System.Globalization;
using System.IO;
using System.Windows;
using System.Windows.Controls;
using NovaApp.Models;
using NovaApp.Services;

namespace NovaApp;

public partial class SettingsWindow : Window
{
    private readonly BackendService _backend;
    private NovaSettings _settings = new();

    public SettingsWindow(BackendService backend)
    {
        InitializeComponent();
        _backend = backend;

        Loaded += async (s, e) =>
        {
            await LoadSettingsFromBackend();
        };
    }

    private async Task LoadSettingsFromBackend()
    {
        try
        {
            _settings = await _backend.GetSettingsAsync();

            // Language
            if (_settings.Language.Equals("tr", StringComparison.OrdinalIgnoreCase))
                CmbLanguage.SelectedIndex = 1;
            else
                CmbLanguage.SelectedIndex = 0;

            // Device
            var dev = _settings.Device.ToLowerInvariant();
            if (dev.Contains("cuda")) CmbDevice.SelectedIndex = 1;
            else if (dev.Contains("directml")) CmbDevice.SelectedIndex = 2;
            else if (dev.Contains("cpu")) CmbDevice.SelectedIndex = 3;
            else CmbDevice.SelectedIndex = 0;

            // Multi-GPU & Workers
            ChkMultiGpu.IsChecked = _settings.MultiGpuEnabled;
            SliderWorkers.Value = Math.Max(1, Math.Min(16, _settings.WorkerThreads));

            // Neural engine & Continuous training
            ChkContinuousTraining.IsChecked = _settings.ContinuousTrainingEnabled;
            TxtLr.Text = _settings.LearningRate.ToString(CultureInfo.InvariantCulture);
            TxtBatchSize.Text = _settings.BatchSize.ToString();
            TxtGrowthThreshold.Text = _settings.GrowthThreshold.ToString(CultureInfo.InvariantCulture);

            // Data & HF
            TxtHfToken.Text = _settings.HfToken;
            ChkCuriosity.IsChecked = _settings.CuriosityEnabled;
            TxtCuriosityTopics.Text = _settings.CuriosityTopics;

            // Curiosity interval
            var cInt = _settings.CuriosityInterval;
            if (cInt <= 10) CmbCuriosityInterval.SelectedIndex = 0;
            else if (cInt <= 25) CmbCuriosityInterval.SelectedIndex = 1;
            else if (cInt <= 50) CmbCuriosityInterval.SelectedIndex = 2;
            else CmbCuriosityInterval.SelectedIndex = 3;

            // Web Server & Mobile
            ChkWebServer.IsChecked = _settings.WebServerEnabled;
            TxtWebPort.Text = _settings.WebServerPort > 0 ? _settings.WebServerPort.ToString() : "8080";
            UpdateWebConnectionUrl();
        }
        catch (Exception ex)
        {
            MessageBox.Show($"Ayarlar yüklenirken hata: {ex.Message}", "Hata", MessageBoxButton.OK, MessageBoxImage.Warning);
        }
    }


    private void TabButton_Checked(object sender, RoutedEventArgs e)
    {
        if (PanelGeneral == null || PanelHardware == null || PanelNeural == null || 
            PanelData == null || PanelWeb == null || PanelAppearance == null || PanelExport == null)
            return;

        // Hide all panels
        PanelGeneral.Visibility = Visibility.Collapsed;
        PanelHardware.Visibility = Visibility.Collapsed;
        PanelNeural.Visibility = Visibility.Collapsed;
        PanelData.Visibility = Visibility.Collapsed;
        PanelWeb.Visibility = Visibility.Collapsed;
        PanelExport.Visibility = Visibility.Collapsed;
        PanelAppearance.Visibility = Visibility.Collapsed;

        // Show the selected panel
        if (sender == TabBtnGeneral)
        {
            PanelGeneral.Visibility = Visibility.Visible;
        }
        else if (sender == TabBtnHardware)
        {
            PanelHardware.Visibility = Visibility.Visible;
        }
        else if (sender == TabBtnNeural)
        {
            PanelNeural.Visibility = Visibility.Visible;
        }
        else if (sender == TabBtnData)
        {
            PanelData.Visibility = Visibility.Visible;
        }
        else if (sender == TabBtnWeb)
        {
            PanelWeb.Visibility = Visibility.Visible;
            UpdateWebConnectionUrl();
        }
        else if (sender == TabBtnExport)
        {
            PanelExport.Visibility = Visibility.Visible;
        }
        else if (sender == TabBtnAppearance)
        {
            PanelAppearance.Visibility = Visibility.Visible;
        }
    }


    private async void BtnExportOnnx_Click(object sender, RoutedEventArgs e)
    {
        BtnExportOnnx.IsEnabled = false;
        TxtExportStatus.Text = "⏳ ONNX model grafı dışa aktarılıyor...";
        try
        {
            var path = await _backend.ExportOnnxAsync();
            if (!string.IsNullOrEmpty(path))
            {
                TxtExportStatus.Text = $"✓ ONNX Modeli başarıyla oluşturuldu:\n{Path.GetFullPath(path)}";
                MessageBox.Show($"ONNX Modeli dışa aktarıldı!\n\nDosya: {Path.GetFullPath(path)}", "ONNX Dışa Aktarma", MessageBoxButton.OK, MessageBoxImage.Information);
            }
            else
            {
                TxtExportStatus.Text = "✗ ONNX dışa aktarma başarısız oldu.";
            }
        }
        catch (Exception ex)
        {
            TxtExportStatus.Text = $"✗ Hata: {ex.Message}";
        }
        finally
        {
            BtnExportOnnx.IsEnabled = true;
        }
    }

    private async void BtnExportZip_Click(object sender, RoutedEventArgs e)
    {
        BtnExportZip.IsEnabled = false;
        TxtExportStatus.Text = "⏳ Model ağırlıkları paketleniyor (.zip)...";
        try
        {
            var path = await _backend.ExportPackageAsync();
            if (!string.IsNullOrEmpty(path))
            {
                TxtExportStatus.Text = $"✓ Model Paketi başarıyla oluşturuldu:\n{Path.GetFullPath(path)}";
                MessageBox.Show($"Model paketi hazır!\n\nDosya: {Path.GetFullPath(path)}", "Model Paketi", MessageBoxButton.OK, MessageBoxImage.Information);
            }
            else
            {
                TxtExportStatus.Text = "✗ Model paketi oluşturulamadı.";
            }
        }
        catch (Exception ex)
        {
            TxtExportStatus.Text = $"✗ Hata: {ex.Message}";
        }
        finally
        {
            BtnExportZip.IsEnabled = true;
        }
    }

    private async void BtnSave_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            // Update settings object
            _settings.Language = CmbLanguage.SelectedIndex == 1 ? "tr" : "en";

            if (CmbDevice.SelectedItem is ComboBoxItem item && item.Tag is string dTag)
            {
                _settings.Device = dTag;
            }

            _settings.MultiGpuEnabled = ChkMultiGpu.IsChecked ?? true;
            _settings.WorkerThreads = (int)SliderWorkers.Value;

            _settings.ContinuousTrainingEnabled = ChkContinuousTraining.IsChecked ?? true;

            if (double.TryParse(TxtLr.Text, NumberStyles.Float, CultureInfo.InvariantCulture, out var lr))
                _settings.LearningRate = lr;

            if (int.TryParse(TxtBatchSize.Text, out var bs))
                _settings.BatchSize = bs;

            if (double.TryParse(TxtGrowthThreshold.Text, NumberStyles.Float, CultureInfo.InvariantCulture, out var gt))
                _settings.GrowthThreshold = gt;

            _settings.HfToken = TxtHfToken.Text.Trim();
            _settings.CuriosityEnabled = ChkCuriosity.IsChecked ?? true;
            _settings.CuriosityTopics = TxtCuriosityTopics.Text.Trim();

            if (CmbCuriosityInterval.SelectedItem is ComboBoxItem cItem && int.TryParse(cItem.Tag?.ToString(), out int cInterval))
            {
                _settings.CuriosityInterval = cInterval;
            }

            // Web Server
            _settings.WebServerEnabled = ChkWebServer.IsChecked ?? false;
            if (int.TryParse(TxtWebPort.Text, out var wp))
            {
                _settings.WebServerPort = wp;
            }

            await _backend.SaveSettingsAsync(_settings);
            DialogResult = true;
            Close();
        }
        catch (Exception ex)
        {
            MessageBox.Show($"Ayarlar kaydedilemedi: {ex.Message}", "Hata", MessageBoxButton.OK, MessageBoxImage.Error);
        }
    }

    private void UpdateWebConnectionUrl()
    {
        int port = int.TryParse(TxtWebPort.Text, out var p) ? p : 8080;
        string ip = "127.0.0.1";
        try
        {
            var host = System.Net.Dns.GetHostEntry(System.Net.Dns.GetHostName());
            foreach (var a in host.AddressList)
            {
                if (a.AddressFamily == System.Net.Sockets.AddressFamily.InterNetwork && !System.Net.IPAddress.IsLoopback(a))
                {
                    ip = a.ToString();
                    break;
                }
            }
        }
        catch { }

        TxtWebConnectionUrl.Text = $"📍 Telefon Bağlantı Adresi: http://{ip}:{port}";
    }

    private void ChkWebServer_Changed(object sender, RoutedEventArgs e)
    {
        if (IsLoaded) UpdateWebConnectionUrl();
    }

    private void BtnOpenWebBrowser_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            int port = int.TryParse(TxtWebPort.Text, out var p) ? p : 8080;
            System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo
            {
                FileName = $"http://localhost:{port}",
                UseShellExecute = true
            });
        }
        catch (Exception ex)
        {
            MessageBox.Show($"Tarayıcı açılamadı: {ex.Message}", "Hata", MessageBoxButton.OK, MessageBoxImage.Warning);
        }
    }

    private async void BtnBulkWiki_Click(object sender, RoutedEventArgs e)
    {
        int count = 500;
        if (CmbBulkCount.SelectedItem is ComboBoxItem bItem && int.TryParse(bItem.Tag?.ToString(), out int bVal))
        {
            count = bVal;
        }

        BtnBulkWiki.IsEnabled = false;
        TxtBulkStatus.Text = $"⏳ {count:N0} Wikipedia makalesi arka planda çekiliyor...";
        try
        {
            string lang = CmbLanguage.SelectedIndex == 1 ? "tr" : "en";
            bool started = await _backend.BulkWikiIngestAsync(count, lang);
            if (started)
            {
                TxtBulkStatus.Text = $"✓ {count:N0} Wikipedia makalesi hafıza tablosuna (nova.db) akıtılmaya başlandı.";
                MessageBox.Show($"Hugging Face üzerinden {count:N0} Wikipedia makalesi indirme görevi başlatıldı.\n\nİndirilen makaleler doğrudan 'Hafıza Grafiği'ne ve eğitim kuyruğuna aktarılacaktır.", "Toplu Wikipedia İndirme", MessageBoxButton.OK, MessageBoxImage.Information);
            }
            else
            {
                TxtBulkStatus.Text = "✗ İndirme işlemi başlatılamadı.";
            }
        }
        catch (Exception ex)
        {
            TxtBulkStatus.Text = $"✗ Hata: {ex.Message}";
        }
        finally
        {
            BtnBulkWiki.IsEnabled = true;
        }
    }

    private void BtnCancel_Click(object sender, RoutedEventArgs e)
    {
        DialogResult = false;
        Close();
    }
}


