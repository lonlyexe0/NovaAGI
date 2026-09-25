using System.ComponentModel;
using System.Runtime.CompilerServices;
using System.Text.Json.Serialization;

namespace NovaApp.Models;

public class GpuDevice
{
    [JsonPropertyName("index")] public int Index { get; set; }
    [JsonPropertyName("name")] public string Name { get; set; } = "";
    [JsonPropertyName("short_name")] public string ShortName { get; set; } = "";
    [JsonPropertyName("backend")] public string Backend { get; set; } = "";
    [JsonPropertyName("vram_mb")] public int VramMb { get; set; }
    [JsonPropertyName("vram_allocated_mb")] public int VramAllocatedMb { get; set; }
    [JsonPropertyName("vram_str")] public string VramStr { get; set; } = "";
    [JsonPropertyName("is_gpu")] public bool IsGpu { get; set; }

    public string Summary => IsGpu ? $"{Backend} · {VramStr}" : "CPU";
}

public class GpuSummary
{
    [JsonPropertyName("name")] public string Name { get; set; } = "CPU";
    [JsonPropertyName("short_name")] public string ShortName { get; set; } = "CPU";
    [JsonPropertyName("backend")] public string Backend { get; set; } = "CPU";
    [JsonPropertyName("count")] public int Count { get; set; }
    [JsonPropertyName("is_multi_gpu")] public bool IsMultiGpu { get; set; }
    [JsonPropertyName("vram_mb")] public int VramMb { get; set; }
    [JsonPropertyName("vram_str")] public string VramStr { get; set; } = "—";
    [JsonPropertyName("is_gpu")] public bool IsGpu { get; set; }
}

public class CpuInfo
{
    [JsonPropertyName("full_name")] public string FullName { get; set; } = "";
    [JsonPropertyName("short_name")] public string ShortName { get; set; } = "CPU";
    [JsonPropertyName("threads")] public int Threads { get; set; } = 1;
}

public class RamInfo
{
    [JsonPropertyName("total_gb")] public double TotalGb { get; set; }
    [JsonPropertyName("free_gb")] public double FreeGb { get; set; }
}

public class HardwareTelemetry
{
    [JsonPropertyName("cpu")] public CpuInfo Cpu { get; set; } = new();
    [JsonPropertyName("gpus")] public List<GpuDevice> Gpus { get; set; } = [];
    [JsonPropertyName("gpu_summary")] public GpuSummary GpuSummary { get; set; } = new();
    [JsonPropertyName("ram")] public RamInfo Ram { get; set; } = new();
    [JsonPropertyName("system_summary")] public string SystemSummary { get; set; } = "";
}

public class ModelArchitecture
{
    [JsonPropertyName("embed_dim")] public int EmbedDim { get; set; }
    [JsonPropertyName("n_heads")] public int NHeads { get; set; }
    [JsonPropertyName("n_layers")] public int NLayers { get; set; }
    [JsonPropertyName("ff_dim")] public int FfDim { get; set; }
    [JsonPropertyName("params")] public long Params { get; set; }
    [JsonPropertyName("growth_count")] public int GrowthCount { get; set; }
}

public class WebServerInfo
{
    [JsonPropertyName("is_running")] public bool IsRunning { get; set; }
    [JsonPropertyName("port")] public int Port { get; set; } = 8080;
    [JsonPropertyName("local_ip")] public string LocalIp { get; set; } = "127.0.0.1";
    [JsonPropertyName("url")] public string Url { get; set; } = "";
}

public class TelemetryPacket
{
    [JsonPropertyName("step")] public long Step { get; set; }
    [JsonPropertyName("loss")] public double Loss { get; set; }
    [JsonPropertyName("learning_rate")] public double LearningRate { get; set; }
    [JsonPropertyName("vocab_size")] public int VocabSize { get; set; }
    [JsonPropertyName("episodic_nodes")] public int EpisodicNodes { get; set; }
    [JsonPropertyName("semantic_nodes")] public int SemanticNodes { get; set; }
    [JsonPropertyName("pending_tasks")] public int PendingTasks { get; set; }
    [JsonPropertyName("untrained")] public int Untrained { get; set; }
    [JsonPropertyName("is_training")] public bool IsTraining { get; set; }
    [JsonPropertyName("device")] public string Device { get; set; } = "cpu";
    [JsonPropertyName("hardware_tier")] public string HardwareTier { get; set; } = "";
    [JsonPropertyName("architecture")] public ModelArchitecture Architecture { get; set; } = new();
    [JsonPropertyName("hardware")] public HardwareTelemetry Hardware { get; set; } = new();
    [JsonPropertyName("web_server")] public WebServerInfo WebServer { get; set; } = new();
}

public abstract class Observable : INotifyPropertyChanged
{
    public event PropertyChangedEventHandler? PropertyChanged;

    protected bool Set<T>(ref T field, T value, [CallerMemberName] string? name = null)
    {
        if (EqualityComparer<T>.Default.Equals(field, value)) return false;
        field = value;
        PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(name));
        return true;
    }

    protected void Raise(string name) => PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(name));
}

public class ChatMessage : Observable
{
    private string _text = "";
    private string _actionText = "";
    private bool _isStreaming;

    public string Role { get; init; } = "user";
    public string Timestamp { get; init; } = DateTime.Now.ToString("HH:mm");
    public string Author { get; init; } = "";

    public string Text
    {
        get => _text;
        set { if (Set(ref _text, value)) Raise(nameof(DisplayText)); }
    }

    /// <summary>Basit markdown işaretleri (**kalın**, `kod`, ``` blokları) temizlenmiş metin.</summary>
    public string DisplayText => MarkdownRegex.Replace(_text, "");

    private static readonly System.Text.RegularExpressions.Regex MarkdownRegex =
        new(@"\*\*|```\w*|`", System.Text.RegularExpressions.RegexOptions.Compiled);
    public bool IsStreaming { get => _isStreaming; set => Set(ref _isStreaming, value); }

    public string ActionText
    {
        get => _actionText;
        set { if (Set(ref _actionText, value)) Raise(nameof(HasAction)); }
    }

    public bool IsUser => Role is "user" or "kullanici";
    public bool IsNova => Role == "nova";
    public bool IsSystem => Role is "system" or "sistem";
    public bool HasAction => !string.IsNullOrWhiteSpace(ActionText);
}

public class NovaSettings
{
    [JsonPropertyName("language")] public string? Language { get; set; } = "en";
    [JsonPropertyName("device")] public string Device { get; set; } = "auto";
    [JsonPropertyName("multi_gpu_enabled")] public bool MultiGpuEnabled { get; set; } = true;
    [JsonPropertyName("worker_threads")] public int WorkerThreads { get; set; } = 4;
    [JsonPropertyName("learning_rate")] public double LearningRate { get; set; } = 0.0003;
    [JsonPropertyName("batch_size")] public int BatchSize { get; set; } = 32;
    [JsonPropertyName("growth_threshold")] public double GrowthThreshold { get; set; } = 0.003;
    [JsonPropertyName("hf_token")] public string HfToken { get; set; } = "";
    [JsonPropertyName("curiosity_enabled")] public bool CuriosityEnabled { get; set; } = true;
    [JsonPropertyName("curiosity_topics")] public string CuriosityTopics { get; set; } = "";
    [JsonPropertyName("curiosity_interval")] public int CuriosityInterval { get; set; } = 20;
    [JsonPropertyName("web_server_enabled")] public bool WebServerEnabled { get; set; }
    [JsonPropertyName("web_server_port")] public int WebServerPort { get; set; } = 8080;
    [JsonPropertyName("continuous_training_enabled")] public bool ContinuousTrainingEnabled { get; set; } = true;
    [JsonPropertyName("theme")] public string Theme { get; set; } = "Nebula";

    [JsonIgnore] public bool IsEnglish => !string.Equals(Language, "tr", StringComparison.OrdinalIgnoreCase);
}

public class GraphNode
{
    [JsonPropertyName("id")] public string Id { get; set; } = "";
    [JsonPropertyName("label")] public string Label { get; set; } = "";
    [JsonPropertyName("type")] public string Type { get; set; } = "episodic";
    [JsonPropertyName("role")] public string Role { get; set; } = "";
    [JsonPropertyName("text")] public string Text { get; set; } = "";
    [JsonPropertyName("date")] public string Date { get; set; } = "";
    [JsonPropertyName("score")] public double Score { get; set; } = 0.5;

    public bool IsSemantic => Type == "semantic";
}

public class GraphLink
{
    [JsonPropertyName("source")] public string Source { get; set; } = "";
    [JsonPropertyName("target")] public string Target { get; set; } = "";
    [JsonPropertyName("weight")] public int Weight { get; set; } = 1;
    [JsonPropertyName("label")] public string Label { get; set; } = "";
}

public class MemoryGraphData
{
    [JsonPropertyName("total_nodes")] public int TotalNodes { get; set; }
    [JsonPropertyName("total_links")] public int TotalLinks { get; set; }
    [JsonPropertyName("nodes")] public List<GraphNode> Nodes { get; set; } = [];
    [JsonPropertyName("links")] public List<GraphLink> Links { get; set; } = [];
}
