import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { leadsApi, campaignsApi, type Lead } from '@/api/client'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import ConfirmationQueue from '@/components/ConfirmationQueue'
import LeadUpload from '@/components/LeadUpload'

type StatusFilter = 'all' | 'needs_confirmation' | 'confirmed' | 'callback'

export default function Leads() {
  const [campaignId, setCampaignId] = useState<number | undefined>()
  const [status, setStatus] = useState<StatusFilter>('all')
  const [page, setPage] = useState(1)
  const [showUpload, setShowUpload] = useState(false)

  const { data: campaigns } = useQuery({
    queryKey: ['campaigns'],
    queryFn: () => campaignsApi.list().then(r => r.data),
  })

  const { data, isLoading } = useQuery({
    queryKey: ['leads', campaignId, status, page],
    queryFn: () =>
      leadsApi.list({ campaign_id: campaignId, status: status === 'all' ? undefined : status, page, size: 20 })
        .then(r => r.data),
  })

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Leads</h1>
        <Button onClick={() => setShowUpload(true)}>Upload CSV</Button>
      </div>

      {showUpload && campaigns && (
        <LeadUpload campaigns={campaigns} onClose={() => setShowUpload(false)} />
      )}

      {/* Confirmation queue (needs_confirmation only) */}
      <ConfirmationQueue campaignId={campaignId} />

      {/* Filters */}
      <div className="flex gap-2 flex-wrap">
        <select
          className="rounded-md border px-3 py-2 text-sm"
          value={campaignId ?? ''}
          onChange={e => { setCampaignId(e.target.value ? Number(e.target.value) : undefined); setPage(1) }}
        >
          <option value="">All campaigns</option>
          {campaigns?.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
        {(['all', 'needs_confirmation', 'confirmed', 'callback'] as StatusFilter[]).map(s => (
          <Button
            key={s}
            size="sm"
            variant={status === s ? 'default' : 'outline'}
            onClick={() => { setStatus(s); setPage(1) }}
          >
            {s === 'all' ? 'All' : s.replace('_', ' ')}
          </Button>
        ))}
      </div>

      {/* Table */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">
            Leads {data ? `(${data.total})` : ''}
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading ? (
            <p className="p-6 text-muted-foreground">Loading…</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-muted/50">
                  <tr>
                    {['Name', 'Phone', 'City', 'Language', 'Status', 'AI Summary', 'Sentiment', 'Confidence'].map(h => (
                      <th key={h} className="px-4 py-3 text-left font-medium text-muted-foreground">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {data?.items.map((lead) => <LeadRow key={lead.id} lead={lead} />)}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Pagination */}
      {data && data.total > 20 && (
        <div className="flex gap-2 justify-end">
          <Button size="sm" variant="outline" disabled={page === 1} onClick={() => setPage(p => p - 1)}>Prev</Button>
          <span className="text-sm self-center">Page {page} of {Math.ceil(data.total / 20)}</span>
          <Button size="sm" variant="outline" disabled={page >= Math.ceil(data.total / 20)} onClick={() => setPage(p => p + 1)}>Next</Button>
        </div>
      )}
    </div>
  )
}

function LeadRow({ lead }: { lead: Lead }) {
  const statusColors: Record<string, string> = {
    new: 'bg-gray-100 text-gray-600',
    queued: 'bg-blue-100 text-blue-700',
    calling: 'bg-yellow-100 text-yellow-700',
    answered: 'bg-purple-100 text-purple-700',
    interested: 'bg-indigo-100 text-indigo-700',
    needs_confirmation: 'bg-orange-100 text-orange-700',
    confirmed: 'bg-green-100 text-green-700',
    attended: 'bg-teal-100 text-teal-700',
    not_interested: 'bg-red-100 text-red-600',
    callback: 'bg-amber-100 text-amber-700',
    no_answer: 'bg-slate-100 text-slate-600',
  }
  return (
    <tr className="hover:bg-muted/30 transition-colors">
      <td className="px-4 py-3 font-medium">{lead.name}</td>
      <td className="px-4 py-3 text-muted-foreground">{lead.phone}</td>
      <td className="px-4 py-3">{lead.city ?? '—'}</td>
      <td className="px-4 py-3 uppercase text-xs">{lead.language}</td>
      <td className="px-4 py-3">
        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${statusColors[lead.status] ?? ''}`}>
          {lead.status}
        </span>
      </td>
      <td className="px-4 py-3 max-w-xs truncate text-muted-foreground">{lead.ai_summary ?? '—'}</td>
      <td className="px-4 py-3">{lead.sentiment_score != null ? `${lead.sentiment_score.toFixed(0)}%` : '—'}</td>
      <td className="px-4 py-3">{lead.confidence_score != null ? `${lead.confidence_score.toFixed(0)}%` : '—'}</td>
    </tr>
  )
}
