#!/bin/sh

REPORT_NAME="FLAC_Metadata_Audit.tsv"
VERIFY_NAME="FLAC_Integrity_Log.txt"

get_tag() {
  file="$1"
  tag="$2"
  metaflac --export-tags-to=- "$file" 2>/dev/null | awk -F= -v key="$tag" 'toupper($1)==toupper(key){sub(/^[^=]*=/,""); gsub(/\t/," "); print; exit}'
}

clean_value() {
  value="$1"
  case "$value" in
    *"Reinserimento solo tag ufficiali/utili"*) echo "" ;;
    *"Rimozione totale tag testuali sporchi"*) echo "" ;;
    *"Lettura tag ufficiali da conservare"*) echo "" ;;
    *"Calcolo AUDIO_PCM_FINGERPRINT_MD5"*) echo "" ;;
    *"Verifica residui"*) echo "" ;;
    *"Fase 1/5"*) echo "" ;;
    *"Fase 2/5"*) echo "" ;;
    *"Fase 3/5"*) echo "" ;;
    *"Fase 4/5"*) echo "" ;;
    *"Fase 5/5"*) echo "" ;;
    *) echo "$value" ;;
  esac
}

set_tag_if_present() {
  file="$1"
  tag="$2"
  value="$3"
  value=$(clean_value "$value")

  if [ -n "$value" ]; then
    metaflac --set-tag="$tag=$value" "$file"
  fi
}

audio_pcm_md5() {
  flac -d -c --force-raw-format --endian=little --sign=signed "$1" 2>/dev/null | md5sum | awk '{print $1}'
}

file_binary_md5() {
  md5sum "$1" | awk '{print $1}'
}

flac_streaminfo_md5() {
  m=$(metaflac --show-md5sum "$1" 2>/dev/null)

  if [ "$m" = "00000000000000000000000000000000" ]; then
    echo "UNSET"
  elif [ -z "$m" ]; then
    echo "UNSET"
  else
    echo "$m"
  fi
}

write_header() {
  printf "FILE\tTITLE\tARTIST\tALBUM\tALBUMARTIST\tDATE\tYEAR\tALBUM_RELEASE_DATE\tDISCNUMBER\tDISCTOTAL\tTRACKNUMBER\tTRACKTOTAL\tISRC\tUPC\tBARCODE\tCOPYRIGHT\tPUBLISHER\tLABEL\tORGANIZATION\tGENRE\tBPM\tREPLAYGAIN_TRACK_GAIN\tREPLAYGAIN_TRACK_PEAK\tFLAC_STREAMINFO_MD5\tAUDIO_PCM_FINGERPRINT_MD5\tFILE_BINARY_MD5\n" > "$OUT"
}

write_row() {
  {
    printf "%s\t" "$file_name"
    printf "%s\t" "$title"
    printf "%s\t" "$artist"
    printf "%s\t" "$album"
    printf "%s\t" "$albumartist"
    printf "%s\t" "$date"
    printf "%s\t" "$year"
    printf "%s\t" "$album_release_date"
    printf "%s\t" "$discnumber"
    printf "%s\t" "$disctotal"
    printf "%s\t" "$tracknumber"
    printf "%s\t" "$tracktotal"
    printf "%s\t" "$isrc"
    printf "%s\t" "$upc"
    printf "%s\t" "$barcode"
    printf "%s\t" "$copyright"
    printf "%s\t" "$publisher"
    printf "%s\t" "$label"
    printf "%s\t" "$organization"
    printf "%s\t" "$genre"
    printf "%s\t" "$bpm"
    printf "%s\t" "$rg_gain"
    printf "%s\t" "$rg_peak"
    printf "%s\t" "$stream_md5"
    printf "%s\t" "$pcm_md5"
    printf "%s\n" "$bin_md5"
  } >> "$OUT"
}

count_flac_in_dir() {
  dir="$1"
  dir_total=0

  for x in "$dir"/*
  do
    if [ ! -f "$x" ]; then
      continue
    fi

    case "$x" in
      *.flac|*.FLAC)
        dir_total=$((dir_total + 1))
        ;;
    esac
  done
}

process_flac_file() {
  f="$1"
  count=$((count + 1))
  file_name="${f##*/}"

  echo "[$count/$dir_total] $file_name"

  title=$(clean_value "$(get_tag "$f" "TITLE")")
  artist=$(clean_value "$(get_tag "$f" "ARTIST")")
  album=$(clean_value "$(get_tag "$f" "ALBUM")")
  albumartist=$(clean_value "$(get_tag "$f" "ALBUMARTIST")")
  date=$(clean_value "$(get_tag "$f" "DATE")")
  year=$(clean_value "$(get_tag "$f" "YEAR")")
  album_release_date=$(clean_value "$(get_tag "$f" "ALBUM_RELEASE_DATE")")
  discnumber=$(clean_value "$(get_tag "$f" "DISCNUMBER")")
  disctotal=$(clean_value "$(get_tag "$f" "DISCTOTAL")")
  tracknumber=$(clean_value "$(get_tag "$f" "TRACKNUMBER")")
  tracktotal=$(clean_value "$(get_tag "$f" "TRACKTOTAL")")
  isrc=$(clean_value "$(get_tag "$f" "ISRC")")
  upc=$(clean_value "$(get_tag "$f" "UPC")")
  barcode=$(clean_value "$(get_tag "$f" "BARCODE")")
  copyright=$(clean_value "$(get_tag "$f" "COPYRIGHT")")
  publisher=$(clean_value "$(get_tag "$f" "PUBLISHER")")
  label=$(clean_value "$(get_tag "$f" "LABEL")")
  organization=$(clean_value "$(get_tag "$f" "ORGANIZATION")")
  genre=$(clean_value "$(get_tag "$f" "GENRE")")
  bpm=$(clean_value "$(get_tag "$f" "BPM")")
  rg_gain=$(clean_value "$(get_tag "$f" "REPLAYGAIN_TRACK_GAIN")")
  rg_peak=$(clean_value "$(get_tag "$f" "REPLAYGAIN_TRACK_PEAK")")

  if [ -z "$barcode" ] && [ -n "$upc" ]; then
    barcode="$upc"
  fi

  if [ -z "$upc" ] && [ -n "$barcode" ]; then
    upc="$barcode"
  fi

  pcm_md5=$(audio_pcm_md5 "$f")
  stream_md5=$(flac_streaminfo_md5 "$f")

  metaflac --remove-all-tags "$f"

  set_tag_if_present "$f" "TITLE" "$title"
  set_tag_if_present "$f" "ARTIST" "$artist"
  set_tag_if_present "$f" "ALBUM" "$album"
  set_tag_if_present "$f" "ALBUMARTIST" "$albumartist"
  set_tag_if_present "$f" "DATE" "$date"
  set_tag_if_present "$f" "YEAR" "$year"
  set_tag_if_present "$f" "ALBUM_RELEASE_DATE" "$album_release_date"
  set_tag_if_present "$f" "DISCNUMBER" "$discnumber"
  set_tag_if_present "$f" "DISCTOTAL" "$disctotal"
  set_tag_if_present "$f" "TRACKNUMBER" "$tracknumber"
  set_tag_if_present "$f" "TRACKTOTAL" "$tracktotal"
  set_tag_if_present "$f" "ISRC" "$isrc"
  set_tag_if_present "$f" "UPC" "$upc"
  set_tag_if_present "$f" "BARCODE" "$barcode"
  set_tag_if_present "$f" "COPYRIGHT" "$copyright"
  set_tag_if_present "$f" "PUBLISHER" "$publisher"
  set_tag_if_present "$f" "LABEL" "$label"
  set_tag_if_present "$f" "ORGANIZATION" "$organization"
  set_tag_if_present "$f" "GENRE" "$genre"
  set_tag_if_present "$f" "BPM" "$bpm"
  set_tag_if_present "$f" "REPLAYGAIN_TRACK_GAIN" "$rg_gain"
  set_tag_if_present "$f" "REPLAYGAIN_TRACK_PEAK" "$rg_peak"

  metaflac --set-tag=AUDIO_PCM_FINGERPRINT_MD5="$pcm_md5" "$f"

  bin_md5=$(file_binary_md5 "$f")

  write_row

  echo "===== $file_name =====" >> "$VERIFY"

  bad=$(metaflac --export-tags-to=- "$f" 2>/dev/null | grep -Ei "TIDAL|QOBUZ|SPOTIFY|AMAZON|DEEZER|APPLE|ITUNES|YOUTUBE|TRACK_MIX|Lavf|Lavc|encoder|LYRICS|UNSYNCEDLYRICS|SYNCEDLYRICS|mediaMetadata|allowStreaming|streamReady|payToStream|premiumStreamingOnly|djReady|stemReady|popularity|album_id|track_id|streamStartDate|Reinserimento")

  if [ -n "$bad" ]; then
    echo "WARNING: residual metadata detected:" >> "$VERIFY"
    echo "$bad" >> "$VERIFY"
  else
    echo "OK: no residual streaming, encoder, lyrics or operational metadata detected." >> "$VERIFY"
  fi

  echo >> "$VERIFY"
  echo "OK: $file_name"
}

process_dir_if_contains_flac() {
  dir="$1"

  count_flac_in_dir "$dir"

  if [ "$dir_total" = "0" ]; then
    return
  fi

  OUT="$dir/$REPORT_NAME"
  VERIFY="$dir/$VERIFY_NAME"

  write_header

  echo "FLAC INTEGRITY CHECK" > "$VERIFY"
  echo "=================================" >> "$VERIFY"
  echo >> "$VERIFY"

  echo
  echo "Cartella: $dir"
  echo "FLAC trovati: $dir_total"

  count=0

  for f in "$dir"/*
  do
    if [ ! -f "$f" ]; then
      continue
    fi

    case "$f" in
      *.flac|*.FLAC)
        process_flac_file "$f"
        ;;
    esac
  done

  echo "Metadata audit created: $OUT"
  echo "Integrity log created"
}

scan_recursive() {
  dir="$1"

  process_dir_if_contains_flac "$dir"

  for item in "$dir"/*
  do
    if [ ! -e "$item" ]; then
      continue
    fi

    if [ -d "$item" ]; then
      scan_recursive "$item"
    fi
  done
}

TARGET="${1:-.}"
scan_recursive "$TARGET"

echo
echo "Operation completed."
echo "Each FLAC folder includes its own metadata audit and integrity log."
