import { useState, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { leadsApi, callsApi, type Lead } from '@/api/client'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import AudioPlayer from '@/components/AudioPlayer'
import { useToast } from '@/hooks/use-toast'
import { CheckCircle, XCircle } from 'lucide-react'

interface Props {
  campaignId?: number
}

export default function ConfirmationQueue({ campaignId }: Props) {
  const { toast } = useToast()
  const qc = useQueryClient()

  const { data } = useQuery({
    queryKey: ['leads', campaignId, 'needs_confirmation'],
    queryFn: () =>
      leadsApi.list({ campaign_id: campaignId, status: 'needs_confirmation', size: 50 }).then(r => r.data),
    refetchInterval: 15_000,
  })

  const approveMutation = useMutation({
    mutationFn: (id: number) => leadsApi.approve(id),
    onSuccess: () => {
      toast({ title: 'Lead approved', description: 'Confirmation SMS sent.' })
      qc.invalidateQueries({ queryKey: ['leads'] })
    },
  })

  const rejectMutation = useMutation({
    mutationFn: (id: number) => leadsApi.reject(id),
    onSuccess: () => {
      toast({ title: 'Lead rejected.' })
      qc.invalidateQueries({ queryKey: ['leads'] })
    },
  })

  const { data: calls } = useQuery({
    queryKey: ['calls-for-confirmation', campaignId],
    queryFn: () => callsApi.list({ campaign_id: campaignId }).then(r => r.data),
  })

  const getRecordingUrl = useCallback((leadId: number) => {
    return calls?.find(c => c.lead_id === leadId && c.recording_url)?.recording_url
  }, [calls])

  if (!data?.total) return null

  return (
    <Card className="border-orange-200">
      <CardHeader>
        <CardTitle className="text-base text-orange-700 flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-orange-500 animate-pulse" />
          Confirmation Queue ({data.total})
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {data.items.map((lead) => (
          <ConfirmationRow
            key={lead.id}
            lead={lead}
            recordingUrl={getRecordingUrl(lead.id)}
            onApprove={() => approveMutation.mutate(lead.id)}
            onReject={() => rejectMutation.mutate(lead.id)}
          />
        ))}
      </CardContent>
    </Card>
  )
}

function ConfirmationRow({
  lead,
  recordingUrl,
  onApprove,
  onReject,
}: {
  lead: Lead
  recordingUrl?: string
  onApprove: () => void
  onReject: () => void
}) {
  return (
    <div className="flex items-start gap-4 rounded-lg border p-4 bg-orange-50/50">
      <div className="flex-1 min-w-0">
        <p className="font-medium">{lead.name}</p>
        <p className="text-sm text-muted-foreground">{lead.phone} · {lead.city}</p>
        {lead.ai_summary && (
          <p className="text-sm mt-1 line-clamp-2 text-gray-600">{lead.ai_summary}</p>
        )}
        <div className="flex gap-3 mt-1 text-xs text-muted-foreground">
          {lead.sentiment_score != null && <span>Sentiment: {lead.sentiment_score.toFixed(0)}%</span>}
          {lead.confidence_score != null && <span>Confidence: {lead.confidence_score.toFixed(0)}%</span>}
          <span>Attendees: {lead.attendees_count}</span>
        </div>
        {recordingUrl && <AudioPlayer url={recordingUrl} />}
      </div>
      <div className="flex gap-2 shrink-0">
        <Button size="sm" onClick={onApprove}>
          <CheckCircle className="h-4 w-4 mr-1" />
          Approve
        </Button>
        <Button size="sm" variant="destructive" onClick={onReject}>
          <XCircle className="h-4 w-4 mr-1" />
          Reject
        </Button>
      </div>
    </div>
  )
}
