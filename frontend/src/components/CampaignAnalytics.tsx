import { useQuery } from '@tanstack/react-query'
import { callsApi } from '@/api/client'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend,
} from 'recharts'

const INTENT_COLORS: Record<string, string> = {
  CONFIRMED: '#22c55e',
  PROBABLY_INTERESTED: '#3b82f6',
  CALLBACK: '#f59e0b',
  NOT_INTERESTED: '#ef4444',
}

export default function CampaignAnalytics() {
  const { data: calls } = useQuery({
    queryKey: ['calls-analytics'],
    queryFn: () => callsApi.list().then(r => r.data),
    refetchInterval: 60_000,
  })

  // Intent distribution
  const intentCounts: Record<string, number> = {}
  calls?.forEach(c => {
    if (c.intent) intentCounts[c.intent] = (intentCounts[c.intent] ?? 0) + 1
  })
  const pieData = Object.entries(intentCounts).map(([name, value]) => ({ name, value }))

  // Daily call volume (last 7 days)
  const dailyCounts: Record<string, number> = {}
  const today = new Date()
  for (let i = 6; i >= 0; i--) {
    const d = new Date(today)
    d.setDate(d.getDate() - i)
    dailyCounts[d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })] = 0
  }
  calls?.forEach(c => {
    if (c.started_at) {
      const label = new Date(c.started_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
      if (dailyCounts[label] !== undefined) dailyCounts[label]++
    }
  })
  const barData = Object.entries(dailyCounts).map(([date, calls]) => ({ date, calls }))

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Call Analytics</CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {pieData.length > 0 && (
          <div>
            <p className="text-sm font-medium text-muted-foreground mb-2">Intent Distribution</p>
            <ResponsiveContainer width="100%" height={180}>
              <PieChart>
                <Pie data={pieData} cx="50%" cy="50%" outerRadius={70} dataKey="value" label>
                  {pieData.map((entry) => (
                    <Cell key={entry.name} fill={INTENT_COLORS[entry.name] ?? '#94a3b8'} />
                  ))}
                </Pie>
                <Legend />
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
        )}
        <div>
          <p className="text-sm font-medium text-muted-foreground mb-2">Daily Call Volume</p>
          <ResponsiveContainer width="100%" height={150}>
            <BarChart data={barData}>
              <XAxis dataKey="date" tick={{ fontSize: 11 }} />
              <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
              <Tooltip />
              <Bar dataKey="calls" fill="#3b82f6" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  )
}
