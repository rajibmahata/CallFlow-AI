import { useRef, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Play, Pause, Volume2 } from 'lucide-react'

export default function AudioPlayer({ url }: { url: string }) {
  const audioRef = useRef<HTMLAudioElement>(null)
  const [playing, setPlaying] = useState(false)
  const [progress, setProgress] = useState(0)

  const toggle = () => {
    if (!audioRef.current) return
    if (playing) {
      audioRef.current.pause()
    } else {
      audioRef.current.play()
    }
    setPlaying(!playing)
  }

  const handleTimeUpdate = () => {
    if (!audioRef.current) return
    const { currentTime, duration } = audioRef.current
    setProgress(duration ? (currentTime / duration) * 100 : 0)
  }

  const handleEnded = () => setPlaying(false)

  return (
    <div className="flex items-center gap-2 mt-2">
      <audio
        ref={audioRef}
        src={url}
        onTimeUpdate={handleTimeUpdate}
        onEnded={handleEnded}
        preload="metadata"
      />
      <Button size="icon" variant="ghost" className="h-7 w-7" onClick={toggle}>
        {playing ? <Pause className="h-3.5 w-3.5" /> : <Play className="h-3.5 w-3.5" />}
      </Button>
      <Volume2 className="h-3.5 w-3.5 text-muted-foreground" />
      <div className="flex-1 h-1.5 rounded-full bg-muted overflow-hidden">
        <div className="h-full bg-primary rounded-full transition-all" style={{ width: `${progress}%` }} />
      </div>
    </div>
  )
}
