import { useState, useCallback } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useWebSocket, type WsMessage } from '@/hooks/useWebSocket'
import { Phone, PhoneOff, Wifi, WifiOff } from 'lucide-react'

interface LiveCall {
  call_id: string
  lead_name: string
  lead_phone: string
  campaign_name: string
  status: 'active' | 'ended'
  duration?: number
  intent?: string
  started_at: string
}

export default function LiveCallMonitor() {
  const [liveCalls, setLiveCalls] = useState<Map<string, LiveCall>>(new Map())

  const handleMessage = useCallback((msg: WsMessage) => {
    if (msg.type === 'call_started') {
      const d = msg.data as Record<string, string>
      setLiveCalls(prev => {
        const next = new Map(prev)
        next.set(d.call_id, {
          call_id: d.call_id,
          lead_name: d.lead_name,
          lead_phone: d.lead_phone,
          campaign_name: d.campaign_name,
          status: 'active',
          started_at: new Date().toISOString(),
        })
        return next
      })
    } else if (msg.type === 'call_ended') {
      const d = msg.data as Record<string, string>
      setLiveCalls(prev => {
        const next = new Map(prev)
        const existing = next.get(d.call_id)
        if (existing) {
          next.set(d.call_id, { ...existing, status: 'ended', intent: d.intent, duration: Number(d.duration) })
          // Remove ended calls after 30s
          setTimeout(() => setLiveCalls(m => { const n = new Map(m); n.delete(d.call_id); return n }), 30_000)
        }
        return next
      })
    }
  }, [])

  const { connected } = useWebSocket(handleMessage)
  const calls = Array.from(liveCalls.values())

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-3">
        <CardTitle className="text-base">Live Calls</CardTitle>
        <div className="flex items-center gap-1 text-xs">
          {connected ? (
            <><Wifi className="h-3 w-3 text-green-500" /><span className="text-green-600">Live</span></>
          ) : (
            <><WifiOff className="h-3 w-3 text-red-500" /><span className="text-red-600">Reconnecting…</span></>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {calls.length === 0 ? (
          <p className="text-sm text-muted-foreground py-4 text-center">No active calls</p>
        ) : (
          <div className="space-y-2">
            {calls.map(call => (
              <div
                key={call.call_id}
                className={`flex items-center gap-3 rounded-lg border p-3 text-sm transition-all ${
                  call.status === 'active' ? 'border-green-200 bg-green-50' : 'border-gray-200 bg-gray-50'
                }`}
              >
                <div className={`p-1.5 rounded-full ${call.status === 'active' ? 'bg-green-100' : 'bg-gray-100'}`}>
                  {call.status === 'active' ? (
                    <Phone className="h-4 w-4 text-green-600" />
                  ) : (
                    <PhoneOff className="h-4 w-4 text-gray-500" />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-medium truncate">{call.lead_name}</p>
                  <p className="text-muted-foreground text-xs">{call.lead_phone} · {call.campaign_name}</p>
                </div>
                <div className="text-right text-xs text-muted-foreground">
                  {call.status === 'active' ? (
                    <span className="text-green-600 font-medium animate-pulse">Active</span>
                  ) : (
                    <span className="capitalize">{call.intent ?? 'ended'}</span>
                  )}
                  {call.duration && <p>{call.duration}s</p>}
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
