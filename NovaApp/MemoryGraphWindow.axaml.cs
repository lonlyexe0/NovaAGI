using System.Text.Json;
using Avalonia.Controls;
using Avalonia.Input;
using Avalonia.Interactivity;
using Avalonia.Platform.Storage;
using Avalonia.Threading;
using NovaApp.Models;
using NovaApp.Services;

namespace NovaApp;

public partial class MemoryGraphWindow : Window
{
    private readonly BackendService _backend;
    private readonly bool _en;
    private readonly DispatcherTimer _timer = new() { Interval = TimeSpan.FromSeconds(5) };
    private MemoryGraphData _data = new();
    private int _limit = 250;
    private bool _loading;

    private string L(string tr, string en) => _en ? en : tr;

    public MemoryGraphWindow() : this(new BackendService(), true) { }

    public MemoryGraphWindow(BackendService backend, bool en)
    {
        InitializeComponent();
        _backend = backend;
        _en = en;
        Localize();
        Graph.NodeSelected += ShowNode;
        _timer.Tick += async (_, _) => { if (ChkLive.IsChecked == true) await LoadAsync(quiet: true); };
        Opened += async (_, _) => { await LoadAsync(); _timer.Start(); };
        Closed += (_, _) => _timer.Stop();
    }

    private void Localize()
    {
        Title = L("Nova AGI — Hafıza grafiği", "Nova AGI — Memory graph");
        TxtTitle.Text = L("🧠 Hafıza grafiği", "🧠 Memory graph");
        ChkLive.Content = L("Canlı", "Live");
        BtnReset.Content = L("⤢ Ortala", "⤢ Reset view");
        BtnRefresh.Content = L("🔄 Yenile", "🔄 Refresh");
        BtnExport.Content = L("💾 JSON", "💾 JSON");
        LegUser.Text = L("Kullanıcı", "User");
        LegNova.Text = L("Nova / sistem", "Nova / system");
        LegFact.Text = L("Bilgi (Wikipedia)", "Fact (Wikipedia)");
        LblFetch.Text = L("📥 Wikipedia'dan öğret", "📥 Teach from Wikipedia");
        TxtFetch.Watermark = L("Konu adı…", "Topic…");
        BtnFetch.Content = L("İndir", "Fetch");
        TxtSearch.Watermark = L("🔍 Grafikte ara…", "🔍 Search the graph…");
        LblNodes.Text = L("Düğüm", "Nodes");
        LblLinks.Text = L("Bağlantı", "Links");
        LblFacts.Text = L("Bilgi düğümü", "Fact nodes");
        ShowNode(null);

        var topics = _en
            ? new[] { "Black hole", "Quantum mechanics", "Neural network", "DNA", "Evolution" }
            : new[] { "Kara delik", "Kuantum mekaniği", "Yapay sinir ağları", "DNA", "Evrim" };
        foreach (var t in topics)
        {
            var b = new Button { Content = "+ " + t, Tag = t, Classes = { "chip" }, Margin = new Avalonia.Thickness(0, 0, 6, 6), FontSize = 11.5 };
            b.Click += async (_, _) => await FetchAsync(t);
            QuickTopics.Children.Add(b);
        }
    }

    private async Task LoadAsync(bool quiet = false)
    {
        if (_loading) return;
        _loading = true;
        if (!quiet) TxtLoading.Text = L("Yükleniyor…", "Loading…");
        try
        {
            var data = await _backend.GetMemoryGraphAsync(Math.Min(_limit / 2, 150), _limit);
            if (!quiet || data.TotalNodes != _data.TotalNodes || data.TotalLinks != _data.TotalLinks)
            {
                _data = data;
                Graph.SetData(data);
                TxtBadge.Text = $"{data.TotalNodes} {L("düğüm", "nodes")} · {data.TotalLinks} {L("bağlantı", "links")}";
                TxtNodes.Text = data.TotalNodes.ToString("N0");
                TxtLinks.Text = data.TotalLinks.ToString("N0");
                TxtFacts.Text = data.Nodes.Count(n => n.IsSemantic).ToString("N0");
            }
            TxtLoading.Text = data.TotalNodes == 0 ? L("Henüz hafıza yok.", "No memories yet.") : "";
        }
        finally { _loading = false; }
    }

    private void ShowNode(GraphNode? n)
    {
        if (n == null)
        {
            TxtNodeTitle.Text = L("Bir düğüme tıklayın", "Click a node");
            TxtNodeMeta.Text = L("Sürükle: kaydır · Tekerlek: yakınlaştır", "Drag: pan · Wheel: zoom");
            TxtNodeBody.Text = "";
            return;
        }
        TxtNodeTitle.Text = n.Label;
        TxtNodeMeta.Text = $"{(n.IsSemantic ? L("📚 Bilgi", "📚 Fact") : $"💬 {n.Role}")} · {n.Date}";
        TxtNodeBody.Text = n.Text.Length > 1500 ? n.Text[..1500] + "…" : n.Text;
    }

    private async Task FetchAsync(string topic)
    {
        topic = topic.Trim();
        if (topic.Length == 0) return;
        BtnFetch.IsEnabled = false;
        var (ok, msg) = await _backend.FetchWikiTopicAsync(topic);
        BtnFetch.IsEnabled = true;
        if (ok)
        {
            TxtFetch.Text = "";
            await LoadAsync();
        }
        TxtNodeTitle.Text = ok ? $"✓ {topic}" : $"✗ {topic}";
        TxtNodeBody.Text = msg;
    }

    private async void BtnFetch_Click(object? sender, RoutedEventArgs e) => await FetchAsync(TxtFetch.Text ?? "");

    private async void TxtFetch_KeyDown(object? sender, KeyEventArgs e)
    {
        if (e.Key == Key.Enter) await FetchAsync(TxtFetch.Text ?? "");
    }

    private void TxtSearch_TextChanged(object? sender, TextChangedEventArgs e) => Graph.Filter = TxtSearch.Text ?? "";
    private async void BtnRefresh_Click(object? sender, RoutedEventArgs e) => await LoadAsync();
    private void BtnReset_Click(object? sender, RoutedEventArgs e) => Graph.ResetView();

    private async void CmbLimit_SelectionChanged(object? sender, SelectionChangedEventArgs e)
    {
        if ((sender as ComboBox)?.SelectedItem is ComboBoxItem { Tag: string t } && int.TryParse(t, out var v))
        {
            _limit = v;
            if (IsLoaded) await LoadAsync();
        }
    }

    private async void BtnExport_Click(object? sender, RoutedEventArgs e)
    {
        var file = await StorageProvider.SaveFilePickerAsync(new FilePickerSaveOptions
        {
            SuggestedFileName = $"nova_memory_graph_{DateTime.Now:yyyyMMdd_HHmm}.json",
            FileTypeChoices = [new FilePickerFileType("JSON") { Patterns = ["*.json"] }],
        });
        if (file == null) return;
        await using var stream = await file.OpenWriteAsync();
        await JsonSerializer.SerializeAsync(stream, _data, new JsonSerializerOptions { WriteIndented = true });
    }
}
