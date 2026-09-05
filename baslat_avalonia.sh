#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT="$ROOT_DIR/NovaApp.Avalonia/NovaApp.Avalonia.csproj"

if [ -x "$HOME/.dotnet/dotnet" ]; then
    export PATH="$HOME/.dotnet:$PATH"
fi

if ! command -v dotnet >/dev/null 2>&1; then
    echo "Hata: .NET SDK bulunamadi. .NET 8 SDK kurup tekrar deneyin."
    exit 1
fi

dotnet run --project "$PROJECT" "$@"
