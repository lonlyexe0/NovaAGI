using Avalonia.Controls;
using Avalonia.Interactivity;
using Avalonia.Media;
using Avalonia.Controls.Shapes;
using NovaApp.Models;
using NovaApp.Services;

namespace NovaApp.Avalonia;

public partial class MemoryGraphWindow : Window
{
    private readonly BackendService _backend;
    private MemoryGraphData _data = new();

    public MemoryGraphWindow() : this(new BackendService())
    {
    }

    public MemoryGraphWindow(BackendService backend)
    {
        InitializeComponent();
        _backend = backend;
        Opened += async (_, _) => await LoadGraphAsync();
    }

    private async Task LoadGraphAsync()
    {
        _data = await _backend.GetMemoryGraphAsync(100, 250);
        NodeCount.Text = $"Dugumler: {_data.TotalNodes} | Baglantilar: {_data.TotalLinks}";
        GraphCanvas.Children.Clear();

        if (_data.Nodes.Count == 0)
        {
            SelectedText.Text = "Henuz hafiza dugumu yok.";
            return;
        }

        var width = GraphCanvas.Bounds.Width > 0 ? GraphCanvas.Bounds.Width : 700;
        var height = GraphCanvas.Bounds.Height > 0 ? GraphCanvas.Bounds.Height : 600;
        for (var i = 0; i < _data.Nodes.Count; i++)
        {
            var node = _data.Nodes[i];
            var angle = i * Math.PI * 2 / Math.Max(1, _data.Nodes.Count);
            var x = width / 2 + Math.Cos(angle) * Math.Min(width, height) * 0.35;
            var y = height / 2 + Math.Sin(angle) * Math.Min(width, height) * 0.35;
            var circle = new Ellipse
            {
                Width = 12,
                Height = 12,
                Fill = node.IsSemantic ? new SolidColorBrush(Color.Parse("#C084FC")) : new SolidColorBrush(Color.Parse("#00E5B3"))
            };
            ToolTip.SetTip(circle, node.Label);
            Canvas.SetLeft(circle, x);
            Canvas.SetTop(circle, y);
            GraphCanvas.Children.Add(circle);
        }
    }

    private async void Refresh_Click(object? sender, RoutedEventArgs e) => await LoadGraphAsync();

    private async void Fetch_Click(object? sender, RoutedEventArgs e)
    {
        var topic = TopicBox.Text?.Trim();
        if (string.IsNullOrWhiteSpace(topic))
            return;

        var result = await _backend.FetchWikiTopicAsync(topic);
        SelectedText.Text = result.Success ? result.Message : $"Hata: {result.Message}";
        if (result.Success)
            await LoadGraphAsync();
    }

    private async void Export_Click(object? sender, RoutedEventArgs e)
    {
        var path = await _backend.ExportPackageAsync();
        SelectedText.Text = string.IsNullOrWhiteSpace(path) ? "Disa aktarma basarisiz." : $"Paket olusturuldu: {path}";
    }
}
