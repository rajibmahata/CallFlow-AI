import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { campaignsApi, type Campaign } from '@/api/client'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useToast } from '@/hooks/use-toast'
import { PlayCircle, PlusCircle } from 'lucide-react'
import CampaignForm from '@/components/CampaignForm'

export default function Campaigns() {
  const [showForm, setShowForm] = useState(false)
  const { data: campaigns, isLoading } = useQuery({
    queryKey: ['campaigns'],
    queryFn: () => campaignsApi.list().then(r => r.data),
  })
  const qc = useQueryClient()
  const { toast } = useToast()

  const startMutation = useMutation({
    mutationFn: (id: number) => campaignsApi.start(id),
    onSuccess: () => {
      toast({ title: 'Campaign started', description: 'Leads are being queued for calls.' })
      qc.invalidateQueries({ queryKey: ['campaigns'] })
    },
    onError: () => toast({ variant: 'destructive', title: 'Error', description: 'Failed to start campaign.' }),
  })

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Campaigns</h1>
        <Button onClick={() => setShowForm(true)}>
          <PlusCircle className="h-4 w-4 mr-2" />
          New Campaign
        </Button>
      </div>

      {showForm && <CampaignForm onClose={() => setShowForm(false)} />}

      {isLoading ? (
        <p className="text-muted-foreground">Loading…</p>
      ) : (
        <div className="grid gap-4">
          {campaigns?.map((c) => (
            <CampaignCard key={c.id} campaign={c} onStart={() => startMutation.mutate(c.id)} />
          ))}
        </div>
      )}
    </div>
  )
}

function CampaignCard({ campaign, onStart }: { campaign: Campaign; onStart: () => void }) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <div>
          <CardTitle className="text-lg">{campaign.name}</CardTitle>
          <p className="text-sm text-muted-foreground">{campaign.event_name} · {new Date(campaign.event_date).toLocaleDateString()}</p>
        </div>
        <div className="flex items-center gap-2">
          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${campaign.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
            {campaign.is_active ? 'Active' : 'Inactive'}
          </span>
          <span className="text-xs px-2 py-0.5 rounded-full bg-blue-100 text-blue-700 font-medium uppercase">
            {campaign.llm_provider}
          </span>
          <Button size="sm" onClick={onStart}>
            <PlayCircle className="h-4 w-4 mr-1" />
            Start
          </Button>
        </div>
      </CardHeader>
      <CardContent className="text-sm text-muted-foreground">
        {campaign.event_location} · Max {campaign.max_daily_calls} calls/day
      </CardContent>
    </Card>
  )
}
