import { useQuery } from '@tanstack/react-query'
import { campaignsApi, callsApi, leadsApi } from '@/api/client'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import LiveCallMonitor from '@/components/LiveCallMonitor'
import CampaignAnalytics from '@/components/CampaignAnalytics'
import { Phone, Users, CheckCircle, TrendingUp } from 'lucide-react'

export default function Dashboard() {
  const { data: campaigns } = useQuery({ queryKey: ['campaigns'], queryFn: () => campaignsApi.list().then(r => r.data) })
  const { data: leadsData } = useQuery({ queryKey: ['leads-all'], queryFn: () => leadsApi.list({ size: 1 }).then(r => r.data) })
  const { data: calls } = useQuery({ queryKey: ['calls-all'], queryFn: () => callsApi.list().then(r => r.data) })

  const confirmedLeads = calls?.filter(c => c.intent === 'CONFIRMED').length ?? 0
  const totalCalls = calls?.length ?? 0
  const conversionRate = totalCalls ? ((confirmedLeads / totalCalls) * 100).toFixed(1) : '0'

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">Dashboard</h1>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard icon={<Megaphone />} label="Active Campaigns" value={campaigns?.filter(c => c.is_active).length ?? 0} />
        <KpiCard icon={<Users />} label="Total Leads" value={leadsData?.total ?? 0} />
        <KpiCard icon={<Phone />} label="Total Calls" value={totalCalls} />
        <KpiCard icon={<CheckCircle />} label="Confirmed" value={`${confirmedLeads} (${conversionRate}%)`} />
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        <LiveCallMonitor />
        <CampaignAnalytics />
      </div>
    </div>
  )
}

function Megaphone() { return <TrendingUp className="h-5 w-5 text-primary" /> }

function KpiCard({ icon, label, value }: { icon: React.ReactNode; label: string; value: string | number }) {
  return (
    <Card>
      <CardContent className="flex items-center gap-4 p-6">
        <div className="p-2 rounded-full bg-primary/10">{icon}</div>
        <div>
          <p className="text-sm text-muted-foreground">{label}</p>
          <p className="text-2xl font-bold">{value}</p>
        </div>
      </CardContent>
    </Card>
  )
}
