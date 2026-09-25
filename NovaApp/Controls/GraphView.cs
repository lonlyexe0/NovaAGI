using Avalonia;
using Avalonia.Controls;
using Avalonia.Input;
using Avalonia.Media;
using Avalonia.Threading;
using NovaApp.Models;

namespace NovaApp.Controls;

/// <summary>
/// Hafıza grafiği: kuvvet yönlendirmeli yerleşim (arka planda hesaplanır),
/// fare tekerleğiyle yakınlaştırma, sürükleyerek kaydırma, tıklayarak seçme.
/// Binlerce ayrı UI öğesi yerine tek Render çağrısında çizilir.
/// </summary>
public class GraphView : Control
{
    private sealed class Node
    {
        public required GraphNode Data;
        public double X, Y, Vx, Vy;
        public int Degree;
    }

    private List<Node> _nodes = [];
    private List<(Node A, Node B, int W)> _links = [];
    private readonly Dictionary<string, (double X, double Y)> _memory = [];
    private Node? _selected, _hover;
    private string _filter = "";
    private double _zoom = 1, _panX, _panY;
    private Point? _dragStart;
    private (double X, double Y) _panStart;
    private CancellationTokenSource? _layoutCts;

    private static readonly IBrush EpisodicBrush = new SolidColorBrush(Color.Parse("#7AA2FF"));
    private static readonly IBrush SemanticBrush = new SolidColorBrush(Color.Parse("#A78BFA"));
    private static readonly IBrush UserBrush = new SolidColorBrush(Color.Parse("#34D399"));
    private static readonly IBrush DimBrush = new SolidColorBrush(Color.Parse("#2A3144"));
    private static readonly IBrush LabelBrush = new SolidColorBrush(Color.Parse("#C9D0E2"));
    private static readonly IPen LinkPen = new Pen(new SolidColorBrush(Color.Parse("#334A6EAA")), 1);
    private static readonly IPen HiLinkPen = new Pen(new SolidColorBrush(Color.Parse("#AA7AA2FF")), 1.6);
    private static readonly IPen RingPen = new Pen(Brushes.White, 2);

    public event Action<GraphNode?>? NodeSelected;

    public GraphView()
    {
        ClipToBounds = true;
        Cursor = new Cursor(StandardCursorType.Hand);
    }

    public string Filter
    {
        get => _filter;
        set { _filter = value.Trim(); InvalidateVisual(); }
    }

    public void SetData(MemoryGraphData data)
    {
        var map = data.Nodes.ToDictionary(n => n.Id, n => new Node { Data = n });
        var rnd = new Random(42);
        foreach (var n in map.Values)
        {
            if (_memory.TryGetValue(n.Data.Id, out var p)) { n.X = p.X; n.Y = p.Y; }
            else
            {
                var r = n.Data.IsSemantic ? 0.75 : 0.4;
                var a = rnd.NextDouble() * Math.PI * 2;
                n.X = Math.Cos(a) * r + rnd.NextDouble() * 0.1;
                n.Y = Math.Sin(a) * r + rnd.NextDouble() * 0.1;
            }
        }
        var links = new List<(Node, Node, int)>();
        foreach (var l in data.Links)
        {
            if (map.TryGetValue(l.Source, out var a) && map.TryGetValue(l.Target, out var b))
            {
                links.Add((a, b, l.Weight));
                a.Degree++;
                b.Degree++;
            }
        }
        _nodes = map.Values.ToList();
        _links = links;
        if (_selected != null && !map.ContainsKey(_selected.Data.Id)) _selected = null;
        RunLayout();
    }

    private void RunLayout()
    {
        _layoutCts?.Cancel();
        var cts = _layoutCts = new CancellationTokenSource();
        var nodes = _nodes;
        var links = _links;
        Task.Run(() =>
        {
            var n = nodes.Count;
            if (n == 0) return;
            var k = Math.Sqrt(4.0 / n);                 // ideal kenar uzunluğu (2x2 alan)
            var cut2 = 9 * k * k;                       // 3k ötesinde itme yok → kopuk düğümler uzaklaşmaz
            var temp = 0.12;
            for (var it = 0; it < 220 && !cts.IsCancellationRequested; it++)
            {
                foreach (var v in nodes) { v.Vx = 0; v.Vy = 0; }
                for (var i = 0; i < n; i++)
                {
                    var a = nodes[i];
                    for (var j = i + 1; j < n; j++)
                    {
                        var b = nodes[j];
                        var dx = a.X - b.X; var dy = a.Y - b.Y;
                        var d2 = dx * dx + dy * dy + 1e-6;
                        if (d2 > cut2) continue;
                        var f = k * k / d2;                     // itme
                        a.Vx += dx * f; a.Vy += dy * f;
                        b.Vx -= dx * f; b.Vy -= dy * f;
                    }
                }
                foreach (var (a, b, w) in links)
                {
                    var dx = a.X - b.X; var dy = a.Y - b.Y;
                    var d = Math.Sqrt(dx * dx + dy * dy) + 1e-6;
                    var f = d / k * Math.Min(w, 4) * 0.5;       // çekme
                    a.Vx -= dx * f; a.Vy -= dy * f;
                    b.Vx += dx * f; b.Vy += dy * f;
                }
                foreach (var v in nodes)
                {
                    var g = v.Degree == 0 ? 0.2 : 0.08;          // merkeze çekim
                    v.Vx -= v.X * g; v.Vy -= v.Y * g;
                    var len = Math.Sqrt(v.Vx * v.Vx + v.Vy * v.Vy) + 1e-9;
                    var step = Math.Min(len, temp);
                    v.X += v.Vx / len * step; v.Y += v.Vy / len * step;
                }
                temp *= 0.975;
                if (it % 20 == 0) Dispatcher.UIThread.Post(InvalidateVisual);
            }
            if (cts.IsCancellationRequested) return;
            lock (_memory)
                foreach (var v in nodes) _memory[v.Data.Id] = (v.X, v.Y);
            Dispatcher.UIThread.Post(InvalidateVisual);
        }, cts.Token);
    }

    private double _fit = 1;   // yerleşimi görünür alana sığdırma katsayısı
    private double Scale => Math.Min(Bounds.Width, Bounds.Height) * 0.44 * _zoom * _fit;
    private Point ToScreen(Node n) => new(Bounds.Width / 2 + _panX + n.X * Scale, Bounds.Height / 2 + _panY + n.Y * Scale);
    private static double Radius(Node n) => (n.Data.IsSemantic ? 5.5 : 4.5) + Math.Min(n.Degree, 12) * 0.45;

    private bool Matches(Node n) =>
        _filter.Length == 0 ||
        n.Data.Label.Contains(_filter, StringComparison.OrdinalIgnoreCase) ||
        n.Data.Text.Contains(_filter, StringComparison.OrdinalIgnoreCase);

    public override void Render(DrawingContext ctx)
    {
        ctx.FillRectangle(Brushes.Transparent, new Rect(Bounds.Size));
        var extent = 0.0;
        foreach (var n in _nodes) extent = Math.Max(extent, Math.Max(Math.Abs(n.X), Math.Abs(n.Y)));
        _fit = extent > 1e-6 ? 1 / extent : 1;
        var focus = _selected ?? _hover;
        foreach (var (a, b, _) in _links)
        {
            var hi = focus != null && (a == focus || b == focus);
            ctx.DrawLine(hi ? HiLinkPen : LinkPen, ToScreen(a), ToScreen(b));
        }
        foreach (var n in _nodes)
        {
            var brush = !Matches(n) ? DimBrush
                : n.Data.IsSemantic ? SemanticBrush
                : n.Data.Role == "kullanici" ? UserBrush : EpisodicBrush;
            var p = ToScreen(n);
            var r = Radius(n) * Math.Clamp(_zoom, 0.7, 1.6);
            ctx.DrawEllipse(brush, n == focus ? RingPen : null, p, r, r);
        }
        foreach (var n in _nodes)
        {
            var show = n == focus || (_filter.Length > 0 && Matches(n)) || (_zoom > 1.6 && n.Degree >= 3);
            if (!show) continue;
            var label = n.Data.Label.Length > 34 ? n.Data.Label[..34] + "…" : n.Data.Label;
            var ft = new FormattedText(label, System.Globalization.CultureInfo.CurrentCulture,
                FlowDirection.LeftToRight, Typeface.Default, 11, LabelBrush);
            var p = ToScreen(n);
            ctx.DrawText(ft, new Point(p.X - ft.Width / 2, p.Y + Radius(n) + 4));
        }
    }

    private Node? HitTest(Point p)
    {
        Node? best = null;
        var bestD = 12.0 * 12.0;
        foreach (var n in _nodes)
        {
            var s = ToScreen(n);
            var d = (s.X - p.X) * (s.X - p.X) + (s.Y - p.Y) * (s.Y - p.Y);
            if (d < bestD) { bestD = d; best = n; }
        }
        return best;
    }

    protected override void OnPointerPressed(PointerPressedEventArgs e)
    {
        var p = e.GetPosition(this);
        var hit = HitTest(p);
        if (hit != null)
        {
            _selected = hit;
            NodeSelected?.Invoke(hit.Data);
        }
        else
        {
            _dragStart = p;
            _panStart = (_panX, _panY);
            if (_selected != null) { _selected = null; NodeSelected?.Invoke(null); }
        }
        InvalidateVisual();
        e.Handled = true;
    }

    protected override void OnPointerMoved(PointerEventArgs e)
    {
        var p = e.GetPosition(this);
        if (_dragStart is { } s)
        {
            _panX = _panStart.X + p.X - s.X;
            _panY = _panStart.Y + p.Y - s.Y;
            InvalidateVisual();
            return;
        }
        var hover = HitTest(p);
        if (hover != _hover)
        {
            _hover = hover;
            ToolTip.SetTip(this, hover == null ? null : $"{hover.Data.Label}\n{hover.Data.Date}");
            InvalidateVisual();
        }
    }

    protected override void OnPointerReleased(PointerReleasedEventArgs e) => _dragStart = null;

    protected override void OnPointerWheelChanged(PointerWheelEventArgs e)
    {
        var p = e.GetPosition(this);
        var old = _zoom;
        _zoom = Math.Clamp(_zoom * (e.Delta.Y > 0 ? 1.15 : 1 / 1.15), 0.3, 6);
        // İmleç altındaki noktayı sabit tut
        var cx = Bounds.Width / 2 + _panX;
        var cy = Bounds.Height / 2 + _panY;
        _panX += (p.X - cx) * (1 - _zoom / old);
        _panY += (p.Y - cy) * (1 - _zoom / old);
        InvalidateVisual();
        e.Handled = true;
    }

    public void ResetView()
    {
        _zoom = 1;
        _panX = _panY = 0;
        InvalidateVisual();
    }
}
