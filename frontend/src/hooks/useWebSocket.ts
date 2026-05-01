import { useEffect, useRef, useState, useCallback } from 'react'
import { useAuthStore } from '@/stores/authStore'

export interface WsMessage {
  type: 'call_started' | 'call_ended' | 'ping'
  data: Record<string, unknown>
}

export function useWebSocket(onMessage?: (msg: WsMessage) => void) {
  const [connected, setConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)
  const token = useAuthStore((s) => s.token)

  const connect = useCallback(() => {
    if (!token) return
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const url = `${protocol}://${window.location.host}/ws/calls?token=${token}`
    const ws = new WebSocket(url)

    ws.onopen = () => setConnected(true)
    ws.onclose = () => {
      setConnected(false)
      // Reconnect after 5s
      setTimeout(connect, 5000)
    }
    ws.onmessage = (event) => {
      try {
        const msg: WsMessage = JSON.parse(event.data)
        onMessage?.(msg)
      } catch {
        // ignore malformed messages
      }
    }
    wsRef.current = ws
  }, [token, onMessage])

  useEffect(() => {
    connect()
    return () => {
      wsRef.current?.close()
    }
  }, [connect])

  return { connected }
}
