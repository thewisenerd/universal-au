YTDL="yt-dlp"

"$YTDL" \
  --verbose --force-ipv4 \
  --ignore-errors --no-continue --no-overwrites \
  --download-archive archive.log \
  --write-description --write-info-json \
  --match-filter "!is_live & !live" \
  --output "%(channel)s/%(uploader)s - %(upload_date)s - %(title)s/%(uploader)s - %(upload_date)s - %(title)s [%(id)s].%(ext)s" \
  --throttled-rate 100K \
  --batch-file "source.txt" \
  --skip-download --youtube-skip-dash-manifest \
  | tee "output.log"
