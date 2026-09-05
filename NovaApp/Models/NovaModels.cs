using System.ComponentModel;
using System.Text.Json.Serialization;

namespace NovaApp.Models;

public class GpuDevice
{
    [JsonPropertyName("index")]
    public int Index { get; set; }

    [JsonPropertyName("name")]
    public string Name { get; set; } = string.Empty;

    [JsonPropertyName("short_name")]
    public string ShortName { get; set; } = string.Empty;

    [JsonPropertyName("backend")]
    public string Backend { get; set; } = string.Empty;

    [JsonPropertyName("vram_mb")]
    public int VramMb { get; set; }

    [JsonPropertyName("vram_allocated_mb")]
    public int VramAllocatedMb { get; set; }

    [JsonPropertyName("vram_str")]
    public string VramStr { get; set; } = string.Empty;

    [JsonPropertyName("is_gpu")]
    public bool IsGpu { get; set; }
}

public class GpuSummary
{
    [JsonPropertyName("name")]
    public string Name { get; set; } = "Yok (CPU Modu)";

    [JsonPropertyName("short_name")]
    public string ShortName { get; set; } = "CPU";

    [JsonPropertyName("backend")]
    public string Backend { get; set; } = "CPU";

    [JsonPropertyName("count")]
    public int Count { get; set; } = 0;

    [JsonPropertyName("is_multi_gpu")]
    public bool IsMultiGpu { get; set; } = false;

    [JsonPropertyName("vram_mb")]
    public int VramMb { get; set; }

    [JsonPropertyName("vram_str")]
    public string VramStr { get; set; } = "—";

    [JsonPropertyName("is_gpu")]
    public bool IsGpu { get; set; }
}

public class CpuInfo
{
    [JsonPropertyName("full_name")]
    public string FullName { get; set; } = string.Empty;

    [JsonPropertyName("short_name")]
    public string ShortName { get; set; } = "CPU";

    [JsonPropertyName("threads")]
    public int Threads { get; set; } = 1;
}

public class RamInfo
{
    [JsonPropertyName("total_gb")]
    public double TotalGb { get; set; }

    [JsonPropertyName("free_gb")]
    public double FreeGb { get; set; }
}

public class HardwareTelemetry
{
    [JsonPropertyName("cpu")]
    public CpuInfo Cpu { get; set; } = new();

    [JsonPropertyName("gpus")]
    public List<GpuDevice> Gpus { get; set; } = [];

    [JsonPropertyName("gpu_summary")]
    public GpuSummary GpuSummary { get; set; } = new();

    [JsonPropertyName("ram")]
    public RamInfo Ram { get; set; } = new();

    [JsonPropertyName("system_summary")]
    public string SystemSummary { get; set; } = string.Empty;
}

public class ModelArchitecture
{
    [JsonPropertyName("embed_dim")]
    public int EmbedDim { get; set; } = 128;

    [JsonPropertyName("n_heads")]
    public int NHeads { get; set; } = 4;

    [JsonPropertyName("n_layers")]
    public int NLayers { get; set; } = 2;

    [JsonPropertyName("ff_dim")]
    public int FfDim { get; set; } = 512;

    [JsonPropertyName("params")]
    public long Params { get; set; }

    [JsonPropertyName("growth_count")]
    public int GrowthCount { get; set; }
}

public class TelemetryPacket
{
    [JsonPropertyName("type")]
    public string Type { get; set; } = "telemetry";

    [JsonPropertyName("step")]
    public long Step { get; set; }

    [JsonPropertyName("loss")]
    public double Loss { get; set; }

    [JsonPropertyName("learning_rate")]
    public double LearningRate { get; set; }

    [JsonPropertyName("vocab_size")]
    public int VocabSize { get; set; }

    [JsonPropertyName("episodic_nodes")]
    public int EpisodicNodes { get; set; }

    [JsonPropertyName("semantic_nodes")]
    public int SemanticNodes { get; set; }

    [JsonPropertyName("pending_tasks")]
    public int PendingTasks { get; set; }

    [JsonPropertyName("is_training")]
    public bool IsTraining { get; set; }

    [JsonPropertyName("architecture")]
    public ModelArchitecture Architecture { get; set; } = new();

    [JsonPropertyName("hardware")]
    public HardwareTelemetry Hardware { get; set; } = new();

    [JsonPropertyName("web_server")]
    public WebServerInfo WebServer { get; set; } = new();
}

public class WebServerInfo
{
    [JsonPropertyName("is_running")]
    public bool IsRunning { get; set; }

    [JsonPropertyName("port")]
    public int Port { get; set; } = 8080;

    [JsonPropertyName("local_ip")]
    public string LocalIp { get; set; } = "127.0.0.1";

    [JsonPropertyName("url")]
    public string Url { get; set; } = "http://localhost:8080";
}

public class ChatMessage : INotifyPropertyChanged
{
    private string _text = string.Empty;

    public string Role { get; set; } = "user"; // "user", "nova", "system"
    public string Text
    {
        get => _text;
        set
        {
            if (_text != value)
            {
                _text = value;
                PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(nameof(Text)));
            }
        }
    }
    public string Timestamp { get; set; } = DateTime.Now.ToString("HH:mm:ss");
    public string ActionText { get; set; } = string.Empty;

    public bool IsUser => Role.Equals("user", StringComparison.OrdinalIgnoreCase) || Role.Equals("kullanici", StringComparison.OrdinalIgnoreCase);
    public bool IsNova => Role.Equals("nova", StringComparison.OrdinalIgnoreCase);
    public bool IsSystem => Role.Equals("system", StringComparison.OrdinalIgnoreCase) || Role.Equals("sistem", StringComparison.OrdinalIgnoreCase);
    public bool HasAction => !string.IsNullOrWhiteSpace(ActionText);

    public event PropertyChangedEventHandler? PropertyChanged;
}

public class NovaSettings
{
    [JsonPropertyName("language")]
    public string Language { get; set; } = "en";

    [JsonPropertyName("device")]
    public string Device { get; set; } = "auto";

    [JsonPropertyName("multi_gpu_enabled")]
    public bool MultiGpuEnabled { get; set; } = true;

    [JsonPropertyName("worker_threads")]
    public int WorkerThreads { get; set; } = 4;

    [JsonPropertyName("learning_rate")]
    public double LearningRate { get; set; } = 0.0003;

    [JsonPropertyName("batch_size")]
    public int BatchSize { get; set; } = 16;

    [JsonPropertyName("growth_threshold")]
    public double GrowthThreshold { get; set; } = 0.003;

    [JsonPropertyName("hf_token")]
    public string HfToken { get; set; } = string.Empty;

    [JsonPropertyName("curiosity_enabled")]
    public bool CuriosityEnabled { get; set; } = true;

    [JsonPropertyName("curiosity_topics")]
    public string CuriosityTopics { get; set; } = string.Empty;

    [JsonPropertyName("curiosity_interval")]
    public int CuriosityInterval { get; set; } = 20;

    [JsonPropertyName("web_server_enabled")]
    public bool WebServerEnabled { get; set; } = false;

    [JsonPropertyName("web_server_port")]
    public int WebServerPort { get; set; } = 8080;

    [JsonPropertyName("continuous_training_enabled")]
    public bool ContinuousTrainingEnabled { get; set; } = true;

    [JsonPropertyName("theme")]
    public string Theme { get; set; } = "Dark";
}



public class GraphNode
{
    [JsonPropertyName("id")]
    public string Id { get; set; } = string.Empty;

    [JsonPropertyName("label")]
    public string Label { get; set; } = string.Empty;

    [JsonPropertyName("type")]
    public string Type { get; set; } = "episodic"; // "episodic", "semantic"

    [JsonPropertyName("role")]
    public string Role { get; set; } = string.Empty;

    [JsonPropertyName("text")]
    public string Text { get; set; } = string.Empty;

    [JsonPropertyName("date")]
    public string Date { get; set; } = string.Empty;

    [JsonPropertyName("score")]
    public double Score { get; set; } = 0.5;

    public bool IsSemantic => Type.Equals("semantic", StringComparison.OrdinalIgnoreCase);
}

public class GraphLink
{
    [JsonPropertyName("source")]
    public string Source { get; set; } = string.Empty;

    [JsonPropertyName("target")]
    public string Target { get; set; } = string.Empty;

    [JsonPropertyName("weight")]
    public int Weight { get; set; } = 1;

    [JsonPropertyName("label")]
    public string Label { get; set; } = string.Empty;
}

public class MemoryGraphData
{
    [JsonPropertyName("total_nodes")]
    public int TotalNodes { get; set; }

    [JsonPropertyName("total_links")]
    public int TotalLinks { get; set; }

    [JsonPropertyName("nodes")]
    public List<GraphNode> Nodes { get; set; } = [];

    [JsonPropertyName("links")]
    public List<GraphLink> Links { get; set; } = [];
}

