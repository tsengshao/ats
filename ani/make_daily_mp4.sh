#!/usr/bin/env bash
set -euo pipefail

FFMPEG="/home/shaoyu/miniforge3/envs/easy/bin/ffmpeg"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="${SCRIPT_DIR}"
FIG_DIR="${BASE_DIR}/fig"
TARGET="${1:-all}"
FORCE="${FORCE:-0}"
TMPDIR_CREATED=""

usage() {
  cat <<'USAGE'
Usage:
  make_daily_mp4.sh [icon|nicam|all]

Notes:
  - You can run this command from any directory.
  - Output files are written to mp4/{icon|nicam}/
  - Set FORCE=1 to overwrite existing mp4 files.
USAGE
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing required command: $1" >&2
    exit 1
  }
}

cleanup() {
  if [[ -n "${TMPDIR_CREATED}" && -d "${TMPDIR_CREATED}" ]]; then
    rm -rf "${TMPDIR_CREATED}"
  fi
}
trap cleanup EXIT

make_video_for_day() {
  local kind="$1"
  local day_dir="$2"
  local day_name daily_img out_dir out_file list_file frame_count frame

  day_name="$(basename "${day_dir}")"
  daily_img="${FIG_DIR}/${kind}/daily/ats_${day_name}.png"
  out_dir="${BASE_DIR}/mp4/${kind}"
  out_file="${out_dir}/${day_name}.mp4"

  if [[ ! -f "${daily_img}" ]]; then
    echo "[skip] ${kind}/${day_name}: missing daily image ${daily_img}" >&2
    return 0
  fi

  mkdir -p "${out_dir}"

  if [[ -f "${out_file}" && "${FORCE}" != "1" ]]; then
    echo "[skip] ${kind}/${day_name}: ${out_file} already exists"
    return 0
  fi

  list_file="${TMPDIR_CREATED}/${kind}_${day_name}.txt"
  {
    printf "file '%s'\n" "${daily_img}"
    printf "duration 2\n"
    while IFS= read -r frame; do
      printf "file '%s'\n" "${frame}"
      printf "duration 0.333333\n"
    done < <(find "${day_dir}" -maxdepth 1 -type f -name 'ats_*.png' | sort)
    # Repeat the last frame once because concat demuxer ignores the final duration otherwise.
    if [[ -n "${frame:-}" ]]; then
      printf "file '%s'\n" "${frame}"
    else
      printf "file '%s'\n" "${daily_img}"
    fi
  } > "${list_file}"

  frame_count="$(wc -l < "${list_file}" | tr -d ' ')"
  if [[ "${frame_count}" -le 1 ]]; then
    echo "[skip] ${kind}/${day_name}: no hourly frames found" >&2
    return 0
  fi

  echo "[make] ${out_file} (${frame_count} frames)"
  "${FFMPEG}" -y \
    -nostdin \
    -f concat \
    -safe 0 \
    -i "${list_file}" \
    -vsync cfr \
    -r 3 \
    -pix_fmt yuv420p \
    -c:v libx264 \
    -movflags +faststart \
    "${out_file}" \
    >/dev/null 2>&1
}

process_kind() {
  local kind="$1"
  local kind_dir

  kind_dir="${FIG_DIR}/${kind}"
  if [[ ! -d "${kind_dir}" ]]; then
    echo "Missing directory: ${kind_dir}" >&2
    exit 1
  fi

  while IFS= read -r day_dir; do
    make_video_for_day "${kind}" "${day_dir}"
  done < <(find "${kind_dir}" -mindepth 1 -maxdepth 1 -type d ! -name daily ! -name mp4 | sort)
}

require_cmd find
require_cmd sort
require_cmd wc

if [[ ! -x "${FFMPEG}" ]]; then
  echo "ffmpeg not found or not executable: ${FFMPEG}" >&2
  exit 1
fi

if [[ ! -d "${FIG_DIR}" ]]; then
  echo "Missing fig directory: ${FIG_DIR}" >&2
  exit 1
fi

TMPDIR_CREATED="$(mktemp -d)"

case "${TARGET}" in
  icon)
    process_kind icon
    ;;
  nicam)
    process_kind nicam
    ;;
  all)
    process_kind icon
    process_kind nicam
    ;;
  -h|--help)
    usage
    ;;
  *)
    usage >&2
    exit 1
    ;;
esac
