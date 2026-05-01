import { useRef, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { leadsApi, type Campaign } from '@/api/client'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { useToast } from '@/hooks/use-toast'
import { Upload } from 'lucide-react'

interface Props {
  campaigns: Campaign[]
  onClose: () => void
}

export default function LeadUpload({ campaigns, onClose }: Props) {
  const [campaignId, setCampaignId] = useState(campaigns[0]?.id)
  const [file, setFile] = useState<File | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)
  const { toast } = useToast()
  const qc = useQueryClient()

  const mutation = useMutation({
    mutationFn: () => leadsApi.upload(campaignId, file!),
    onSuccess: (res) => {
      const d = res.data as { imported: number; skipped: number; duplicates: number }
      toast({ title: `Imported ${d.imported} leads`, description: `Skipped: ${d.skipped}, Duplicates: ${d.duplicates}` })
      qc.invalidateQueries({ queryKey: ['leads'] })
      onClose()
    },
    onError: () => toast({ variant: 'destructive', title: 'Upload failed' }),
  })

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Upload Leads CSV</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div>
          <label className="block text-sm font-medium mb-1">Campaign</label>
          <select
            className="w-full rounded-md border px-3 py-2 text-sm"
            value={campaignId}
            onChange={e => setCampaignId(Number(e.target.value))}
          >
            {campaigns.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">CSV File</label>
          <div
            className="border-2 border-dashed rounded-lg p-6 text-center cursor-pointer hover:border-primary transition-colors"
            onClick={() => fileRef.current?.click()}
          >
            <Upload className="h-8 w-8 mx-auto text-muted-foreground mb-2" />
            <p className="text-sm text-muted-foreground">
              {file ? file.name : 'Click to select CSV file'}
            </p>
          </div>
          <input ref={fileRef} type="file" accept=".csv" className="hidden" onChange={e => setFile(e.target.files?.[0] ?? null)} />
        </div>
        <p className="text-xs text-muted-foreground">
          Required columns: name, phone. Optional: email, age, city, language.
        </p>
        <div className="flex gap-2 justify-end">
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button disabled={!file || mutation.isPending} onClick={() => mutation.mutate()}>
            {mutation.isPending ? 'Uploading…' : 'Upload'}
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
