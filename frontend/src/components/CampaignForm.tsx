import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { campaignsApi, type Campaign } from '@/api/client'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { useToast } from '@/hooks/use-toast'

interface Props {
  onClose: () => void
}

export default function CampaignForm({ onClose }: Props) {
  const [form, setForm] = useState({
    name: '',
    event_name: '',
    event_date: '',
    event_location: '',
    llm_provider: 'openai' as 'openai' | 'deepseek',
    max_daily_calls: 100,
    capacity: '',
  })
  const { toast } = useToast()
  const qc = useQueryClient()

  const mutation = useMutation({
    mutationFn: () => campaignsApi.create({
      ...form,
      capacity: form.capacity ? Number(form.capacity) : undefined,
    }),
    onSuccess: () => {
      toast({ title: 'Campaign created' })
      qc.invalidateQueries({ queryKey: ['campaigns'] })
      onClose()
    },
    onError: () => toast({ variant: 'destructive', title: 'Error', description: 'Failed to create campaign.' }),
  })

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    setForm(prev => ({ ...prev, [e.target.name]: e.target.value }))
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">New Campaign</CardTitle>
      </CardHeader>
      <CardContent>
        <form
          onSubmit={e => { e.preventDefault(); mutation.mutate() }}
          className="grid grid-cols-2 gap-4"
        >
          {[
            { name: 'name', label: 'Campaign Name', type: 'text', required: true },
            { name: 'event_name', label: 'Event Name', type: 'text', required: true },
            { name: 'event_date', label: 'Event Date & Time', type: 'datetime-local', required: true },
            { name: 'event_location', label: 'Location', type: 'text', required: false },
            { name: 'max_daily_calls', label: 'Max Daily Calls', type: 'number', required: true },
            { name: 'capacity', label: 'Capacity (optional)', type: 'number', required: false },
          ].map(({ name, label, type, required }) => (
            <div key={name}>
              <label className="block text-sm font-medium mb-1">{label}</label>
              <input
                type={type}
                name={name}
                required={required}
                className="w-full rounded-md border px-3 py-2 text-sm"
                value={(form as Record<string, string | number>)[name] as string}
                onChange={handleChange}
              />
            </div>
          ))}
          <div>
            <label className="block text-sm font-medium mb-1">LLM Provider</label>
            <select
              name="llm_provider"
              className="w-full rounded-md border px-3 py-2 text-sm"
              value={form.llm_provider}
              onChange={handleChange}
            >
              <option value="openai">OpenAI (GPT-4o)</option>
              <option value="deepseek">DeepSeek</option>
            </select>
          </div>
          <div className="col-span-2 flex gap-2 justify-end">
            <Button type="button" variant="outline" onClick={onClose}>Cancel</Button>
            <Button type="submit" disabled={mutation.isPending}>Create</Button>
          </div>
        </form>
      </CardContent>
    </Card>
  )
}
