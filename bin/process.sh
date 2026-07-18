#!/bin/zsh
# Film-look pipeline: RawTherapee render + halation/grain (+ web export, contact sheets).
# Usage: process.sh <photo-folder> [look] [NN|all] [--web]
#   look = a sibling folder of bin/ containing rawtherapee/*.pp3 and fx.conf
#          (default: boardwalk); NN = two-digit variant number from the pp3 filenames
set -e
DIR="${1:?usage: process.sh <photo-folder> [look] [NN|all] [--web]}"
shift
LOOK=boardwalk; WHICH=all; WEB=0
for a in "$@"; do
  case "$a" in
    --web) WEB=1 ;;
    all) WHICH=all ;;
    [0-9][0-9]) WHICH="$a" ;;
    *) LOOK="$a" ;;
  esac
done
BIN="$(cd "$(dirname "$0")" && pwd)"
LOOKDIR="$BIN/../$LOOK"
if [[ ! -d "$LOOKDIR/rawtherapee" ]]; then
  echo "unknown look '$LOOK' (no $LOOKDIR/rawtherapee)"; exit 1
fi

typeset -A FX
while read -r n a b c; do
  [[ -z "$n" || "$n" == \#* ]] && continue
  FX[$n]="$a $b $c"
done < "$LOOKDIR/fx.conf"

OUT="$DIR/renders/$LOOK"
mkdir -p "$OUT"

for nef in "$DIR"/*.NEF(N) "$DIR"/*.nef(N); do
  base="${$(basename "$nef")%.*}"
  for pp3 in "$LOOKDIR/rawtherapee/"*.pp3(N); do
    fname=$(basename "$pp3")
    [[ "$fname" =~ " ([0-9][0-9]) - " ]] || continue
    n="$match[1]"
    [[ "$WHICH" != "all" && "$WHICH" != "$n" ]] && continue
    jpg="$OUT/${base}_$n.jpg"
    "$BIN/rtcli" -Y -o "$jpg" -j90 -p "$pp3" -c "$nef" >/dev/null 2>&1
    python3 "$BIN/film_fx.py" "$jpg" "$jpg" ${=FX[$n]:-8 1.6 0.5}
    if (( WEB )); then
      mkdir -p "$OUT/web"
      python3 "$BIN/web_export.py" "$jpg" "$OUT/web/${base}_$n.jpg"
    fi
  done
  echo "$base done"
done

python3 "$BIN/contact_sheet.py" "$OUT" "$LOOKDIR"
