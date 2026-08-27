using System.IO;
using System.Text.Json;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Shapes;
using System.Windows.Threading;
using Microsoft.Win32;
using NovaApp.Models;
using NovaApp.Services;

namespace NovaApp;

public partial class MemoryGraphWindow : Window
{
    private readonly BackendService _backend;
    private MemoryGraphData _graphData = new();
    private readonly Dictionary<string, (Point Pos, UIElement Element)> _nodeVisuals = new();
    private string _filterQuery = string.Empty;
    private readonly DispatcherTimer _liveTimer = new();
    private int _limitAni = 100;
    private int _limitBilgi = 300;

    public MemoryGraphWindow(BackendService backend)
    {
        InitializeComponent();
        _backend = backend;

        // Auto-refresh timer (Every 4 seconds)
        _liveTimer.Interval = TimeSpan.FromSeconds(4);
        _liveTimer.Tick += async (s, e) =>
        {
            if (ChkLiveAutoRefresh.IsChecked == true && IsVisible)
            {
                await BackgroundRefreshAsync();
            }
        };

        Loaded += async (s, e) =>
        {
            await LoadGraphDataAsync();
            _liveTimer.Start();
        };

        Closed += (s, e) =>
        {
            _liveTimer.Stop();
        };

        SizeChanged += (s, e) =>
        {
            if (_graphData.Nodes.Count > 0)
                RenderGraph();
        };
    }

    private async Task LoadGraphDataAsync()
    {
        OverlayLoading.Visibility = Visibility.Visible;
        try
        {
            _graphData = await _backend.GetMemoryGraphAsync(_limitAni, _limitBilgi);
            UpdateStats();
            RenderGraph();
        }
        catch (Exception ex)
        {
            MessageBox.Show($"Grafik yüklenemedi: {ex.Message}", "Hata", MessageBoxButton.OK, MessageBoxImage.Warning);
        }
        finally
        {
            OverlayLoading.Visibility = Visibility.Collapsed;
        }
    }

    private async Task BackgroundRefreshAsync()
    {
        try
        {
            var newData = await _backend.GetMemoryGraphAsync(_limitAni, _limitBilgi);
            if (newData.TotalNodes != _graphData.TotalNodes || newData.TotalLinks != _graphData.TotalLinks)
            {
                _graphData = newData;
                UpdateStats();
                RenderGraph();
            }
        }
        catch { }
    }

    private void UpdateStats()
    {
        TxtTotalNodesBadge.Text = $"{_graphData.TotalNodes} Düğüm • {_graphData.TotalLinks} Bağlantı";
        TxtStatNodes.Text = _graphData.TotalNodes.ToString();
        TxtStatLinks.Text = _graphData.TotalLinks.ToString();
        TxtStatTopics.Text = _graphData.Nodes.Count(n => n.IsSemantic).ToString();
    }

    private void RenderGraph()
    {
        GraphCanvas.Children.Clear();
        _nodeVisuals.Clear();

        if (_graphData.Nodes.Count == 0)
            return;

        double width = Math.Max(GraphCanvas.ActualWidth, 650);
        double height = Math.Max(GraphCanvas.ActualHeight, 450);
        double centerX = width / 2;
        double centerY = height / 2;

        var filteredNodes = _graphData.Nodes
            .Where(n => string.IsNullOrWhiteSpace(_filterQuery) ||
                        n.Label.Contains(_filterQuery, StringComparison.OrdinalIgnoreCase) ||
                        n.Text.Contains(_filterQuery, StringComparison.OrdinalIgnoreCase))
            .ToList();

        if (filteredNodes.Count == 0) return;

        // Calculate positions in circular clusters (Episodic on left/inner ring, Semantic on outer/right ring)
        var rand = new Random(42);
        int count = filteredNodes.Count;

        for (int i = 0; i < count; i++)
        {
            var node = filteredNodes[i];
            double angle = (2 * Math.PI * i) / count;
            double radius = node.IsSemantic 
                ? Math.Min(width, height) * 0.36 + rand.Next(-25, 25)
                : Math.Min(width, height) * 0.20 + rand.Next(-18, 18);

            double x = centerX + radius * Math.Cos(angle);
            double y = centerY + radius * Math.Sin(angle);

            // Clamp inside canvas bounds
            x = Math.Clamp(x, 40, width - 40);
            y = Math.Clamp(y, 40, height - 40);

            // Create Visual Node
            var nodeElement = CreateNodeVisual(node);
            Canvas.SetLeft(nodeElement, x - 14);
            Canvas.SetTop(nodeElement, y - 14);

            _nodeVisuals[node.Id] = (new Point(x, y), nodeElement);
        }

        // Draw Links
        foreach (var link in _graphData.Links)
        {
            if (_nodeVisuals.TryGetValue(link.Source, out var src) &&
                _nodeVisuals.TryGetValue(link.Target, out var tgt))
            {
                var line = new Line
                {
                    X1 = src.Pos.X,
                    Y1 = src.Pos.Y,
                    X2 = tgt.Pos.X,
                    Y2 = tgt.Pos.Y,
                    Stroke = new SolidColorBrush(Color.FromArgb(0x55, 0x4A, 0x6E, 0xAA)),
                    StrokeThickness = Math.Clamp(link.Weight * 0.7, 1.0, 3.5)
                };
                GraphCanvas.Children.Add(line);
            }
        }

        // Add Nodes on top of links
        foreach (var kv in _nodeVisuals)
        {
            GraphCanvas.Children.Add(kv.Value.Element);
        }
    }

    private UIElement CreateNodeVisual(GraphNode node)
    {
        var grid = new Grid { Cursor = Cursors.Hand };

        var bgBrush = node.IsSemantic
            ? new SolidColorBrush(Color.FromRgb(0xC0, 0x84, 0xFC))
            : (Brush)FindResource("AccentCyanBrush");

        var border = new Border
        {
            Width = node.IsSemantic ? 24 : 20,
            Height = node.IsSemantic ? 24 : 20,
            CornerRadius = new CornerRadius(12),
            Background = bgBrush,
            BorderBrush = new SolidColorBrush(Color.FromArgb(0x88, 0xFF, 0xFF, 0xFF)),
            BorderThickness = new Thickness(1.5),
            ToolTip = $"{node.Label}\n{node.Date}"
        };

        // Text label tag
        var lbl = new TextBlock
        {
            Text = Truncate(node.Label, 18),
            FontSize = 9.5,
            FontWeight = FontWeights.SemiBold,
            Foreground = (Brush)FindResource("TextPrimaryBrush"),
            Margin = new Thickness(-25, 24, 0, 0),
            HorizontalAlignment = HorizontalAlignment.Center,
            TextAlignment = TextAlignment.Center,
            MaxWidth = 90,
            TextTrimming = TextTrimming.CharacterEllipsis
        };

        grid.Children.Add(border);
        grid.Children.Add(lbl);

        // Click selection handler
        grid.MouseLeftButtonDown += (s, e) =>
        {
            e.Handled = true;
            SelectNode(node);
        };

        return grid;
    }

    private void SelectNode(GraphNode node)
    {
        TxtSelectedTitle.Text = node.Label;
        TxtSelectedType.Text = $"Tür: {(node.IsSemantic ? "📚 Semantik Bilgi (Wikipedia)" : $"💬 Epizodik Anı ({node.Role})")}";
        TxtSelectedDate.Text = $"Tarih: {node.Date}";
        TxtSelectedContent.Text = node.Text;
    }

    private void TxtSearch_TextChanged(object sender, TextChangedEventArgs e)
    {
        _filterQuery = TxtSearch.Text.Trim();
        RenderGraph();
    }

    private async void BtnRefresh_Click(object sender, RoutedEventArgs e)
    {
        await LoadGraphDataAsync();
    }

    private void ChkLiveAutoRefresh_Changed(object sender, RoutedEventArgs e)
    {
        if (ChkLiveAutoRefresh.IsChecked == true)
            _liveTimer.Start();
        else
            _liveTimer.Stop();
    }

    private async void CmbLimit_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (CmbLimit.SelectedItem is ComboBoxItem item && int.TryParse(item.Tag?.ToString(), out int val))
        {
            _limitBilgi = val;
            _limitAni = Math.Min(val / 2, 100);
            if (IsLoaded)
            {
                await LoadGraphDataAsync();
            }
        }
    }

    private async void BtnFetchWiki_Click(object sender, RoutedEventArgs e)
    {
        var topic = TxtWikiFetchQuery.Text.Trim();
        if (string.IsNullOrEmpty(topic)) return;

        BtnFetchWiki.IsEnabled = false;
        BtnFetchWiki.Content = "⏳...";
        try
        {
            var (success, msg) = await _backend.FetchWikiTopicAsync(topic);
            if (success)
            {
                TxtWikiFetchQuery.Clear();
                await LoadGraphDataAsync();
            }
            else
            {
                MessageBox.Show(msg, "Wikipedia", MessageBoxButton.OK, MessageBoxImage.Information);
            }
        }
        finally
        {
            BtnFetchWiki.IsEnabled = true;
            BtnFetchWiki.Content = "📥 İndir";
        }
    }

    private void TxtWikiFetchQuery_KeyDown(object sender, KeyEventArgs e)
    {
        if (e.Key == Key.Enter)
        {
            BtnFetchWiki_Click(sender, e);
        }
    }

    private void QuickWikiChip_Click(object sender, RoutedEventArgs e)
    {
        if (sender is Button btn && btn.Tag is string topic)
        {
            TxtWikiFetchQuery.Text = topic;
            BtnFetchWiki_Click(sender, e);
        }
    }

    private void BtnExportJson_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            var sfd = new SaveFileDialog
            {
                Filter = "JSON Dosyası (*.json)|*.json",
                FileName = $"nova_hafiza_grafigi_{DateTime.Now:yyyyMMdd_HHmm}.json"
            };

            if (sfd.ShowDialog() == true)
            {
                var json = JsonSerializer.Serialize(_graphData, new JsonSerializerOptions { WriteIndented = true });
                File.WriteAllText(sfd.FileName, json);
                MessageBox.Show($"Hafıza grafiği başarıyla kaydedildi:\n{sfd.FileName}", "Başarılı", MessageBoxButton.OK, MessageBoxImage.Information);
            }
        }
        catch (Exception ex)
        {
            MessageBox.Show($"Dışa aktarma hatası: {ex.Message}", "Hata", MessageBoxButton.OK, MessageBoxImage.Error);
        }
    }

    private void GraphCanvas_MouseLeftButtonDown(object sender, MouseButtonEventArgs e)
    {
        // Deselect if background clicked
        TxtSelectedTitle.Text = "(Grafikten bir düğüme tıklayın)";
        TxtSelectedType.Text = "Tür: —";
        TxtSelectedDate.Text = "Tarih: —";
        TxtSelectedContent.Text = "Grafikten incelemek istediğiniz hafıza veya Wikipedia düğümüne tıklayınız.";
    }

    private static string Truncate(string val, int max) =>
        string.IsNullOrEmpty(val) ? "" : (val.Length <= max ? val : val[..max] + "..");
}
