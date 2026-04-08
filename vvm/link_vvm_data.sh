#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
HOST_SHORT=${HOSTNAME:-$(hostname -s)}
HOST_SHORT=${HOST_SHORT%%.*}

SOURCE_DIRS=()
NICAM_PATTERNS=()
ICON_PATTERNS=()
OBS_PATTERNS=()

configure_host() {
  case "${HOST_SHORT}" in
    ilgn02|ilgn01)
      SOURCE_DIRS=(
        "/work1/umbrella0c/VVM/DATA"
      )

      NICAM_PATTERNS=(
        "tpe_*_nicam"
      )

      ICON_PATTERNS=(
        "tpe_*_icon"
      )

      OBS_PATTERNS=(
        # Example: "obs_*"
      )
      ;;

    cloud|mogamd)
      SOURCE_DIRS=(
	"/data2/VVM/taiwanvvm_summer"
	"/data3/VVM/taiwanvvm_summer_gsrm"
      )

      NICAM_PATTERNS=(
        "tpe_*_nicam"
      )

      ICON_PATTERNS=(
        "tpe_*_icon"
      )

      OBS_PATTERNS=(
        "tpe_*_at*"
      ) 
      ;;

    # Example:
    # xxx)
    #   SOURCE_DIRS=(
    #     "/path/to/data1"
    #     "/path/to/data2"
    #   )
    #   NICAM_PATTERNS=(
    #     "tpe_*_nicam"
    #     "expA_*"
    #   )
    #   ICON_PATTERNS=(
    #     "tpe_*_icon"
    #   )
    #   OBS_PATTERNS=(
    #     "obs_*"
    #   )
    #   ;;

    *)
      printf 'Unsupported host: %s\n' "${HOST_SHORT}" >&2
      printf 'Edit %s and add this host in configure_host().\n' "${BASH_SOURCE[0]}" >&2
      return 1
      ;;
  esac
}

ensure_category_dir() {
  local category=$1
  mkdir -p "${SCRIPT_DIR}/${category}"
}

link_matches() {
  local category=$1
  shift
  local patterns=("$@")
  local src_dir
  local pattern
  local src_path
  local base_name
  local matched=1

  ensure_category_dir "${category}"
  shopt -s nullglob

  for src_dir in "${SOURCE_DIRS[@]}"; do
    [[ -d "${src_dir}" ]] || continue

    for pattern in "${patterns[@]}"; do
      for src_path in "${src_dir}"/${pattern}; do
        [[ -d "${src_path}" ]] || continue
        base_name=$(basename "${src_path}")
        ln -sfn "${src_path}" "${SCRIPT_DIR}/${category}/${base_name}"
        matched=0
      done
    done
  done

  shopt -u nullglob
  return ${matched}
}

main() {
  local nicam_found=1
  local icon_found=1
  local obs_found=1

  configure_host

  ensure_category_dir "nicam"
  ensure_category_dir "icon"
  ensure_category_dir "obs"

  if [[ ${#NICAM_PATTERNS[@]} -gt 0 ]]; then
    link_matches "nicam" "${NICAM_PATTERNS[@]}" || nicam_found=0
  fi

  if [[ ${#ICON_PATTERNS[@]} -gt 0 ]]; then
    link_matches "icon" "${ICON_PATTERNS[@]}" || icon_found=0
  fi

  if [[ ${#OBS_PATTERNS[@]} -gt 0 ]]; then
    link_matches "obs" "${OBS_PATTERNS[@]}" || obs_found=0
  fi

  printf 'Host: %s\n' "${HOST_SHORT}"
  printf 'Base directory: %s\n' "${SCRIPT_DIR}"
  printf 'Source directories:\n'
  printf '  %s\n' "${SOURCE_DIRS[@]}"

  [[ ${#NICAM_PATTERNS[@]} -eq 0 || ${nicam_found} -eq 1 ]] || printf 'No nicam match found.\n' >&2
  [[ ${#ICON_PATTERNS[@]} -eq 0 || ${icon_found} -eq 1 ]] || printf 'No icon match found.\n' >&2
  [[ ${#OBS_PATTERNS[@]} -eq 0 || ${obs_found} -eq 1 ]] || printf 'No obs match found.\n' >&2
}

main "$@"
