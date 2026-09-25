using Avalonia;
using Avalonia.Controls;
using Avalonia.Media;

namespace NovaApp.Controls;

/// <summary>Son N loss değerini alan grafiği olarak çizer (hafif, tek Render çağrısı).</summary>
public class LossChart : Control
{
    private readonly List<double> _values = [];
    private const int Capacity = 120;

    private static readonly IPen GridPen = new Pen(new SolidColorBrush(Color.Parse("#242B3D")), 1, new DashStyle([2, 4], 0));
    private static readonly IPen LinePen = new Pen(new SolidColorBrush(Color.Parse("#7AA2FF")), 2, lineJoin: PenLineJoin.Round);
    private static readonly IBrush Fill = new LinearGradientBrush
    {
        StartPoint = new RelativePoint(0, 0, RelativeUnit.Relative),
        EndPoint = new RelativePoint(0, 1, RelativeUnit.Relative),
        GradientStops = { new GradientStop(Color.Parse("#557AA2FF"), 0), new GradientStop(Color.Parse("#007AA2FF"), 1) },
    };
    private static readonly IBrush DotBrush = new SolidColorBrush(Color.Parse("#A78BFA"));
    private static readonly IBrush LabelBrush = new SolidColorBrush(Color.Parse("#5F6880"));

    public double? Min => _values.Count > 0 ? _values.Min() : null;
    public double? Max => _values.Count > 0 ? _values.Max() : null;

    public void Push(double value)
    {
        if (double.IsNaN(value) || double.IsInfinity(value) || value <= 0) return;
        _values.Add(value);
        if (_values.Count > Capacity) _values.RemoveAt(0);
        InvalidateVisual();
    }

    public override void Render(DrawingContext ctx)
    {
        var w = Bounds.Width;
        var h = Bounds.Height;
        const double pad = 6;
        for (var i = 0; i <= 2; i++)
        {
            var y = pad + (h - 2 * pad) * i / 2.0;
            ctx.DrawLine(GridPen, new Point(pad, y), new Point(w - pad, y));
        }

        if (_values.Count < 2)
        {
            var ft = new FormattedText("—", System.Globalization.CultureInfo.InvariantCulture,
                FlowDirection.LeftToRight, Typeface.Default, 12, LabelBrush);
            ctx.DrawText(ft, new Point(w / 2 - ft.Width / 2, h / 2 - ft.Height / 2));
            return;
        }

        var min = _values.Min();
        var max = _values.Max();
        if (max - min < 1e-4) max = min + 1e-2;

        Point P(int i) => new(
            pad + (w - 2 * pad) * i / (_values.Count - 1),
            h - pad - (_values[i] - min) / (max - min) * (h - 2 * pad));

        var line = new StreamGeometry();
        var area = new StreamGeometry();
        using (var lc = line.Open())
        using (var ac = area.Open())
        {
            lc.BeginFigure(P(0), false);
            ac.BeginFigure(new Point(pad, h - pad), true);
            ac.LineTo(P(0));
            for (var i = 1; i < _values.Count; i++)
            {
                lc.LineTo(P(i));
                ac.LineTo(P(i));
            }
            ac.LineTo(new Point(w - pad, h - pad));
            lc.EndFigure(false);
            ac.EndFigure(true);
        }
        ctx.DrawGeometry(Fill, null, area);
        ctx.DrawGeometry(null, LinePen, line);
        ctx.DrawEllipse(DotBrush, null, P(_values.Count - 1), 3.5, 3.5);
    }
}
