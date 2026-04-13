import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'

export function ActivityLog() {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Attivita Recente</CardTitle>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Ora</TableHead>
              <TableHead>Agente</TableHead>
              <TableHead>Azione</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow>
              <TableCell
                colSpan={3}
                className="text-center text-sm text-muted-foreground py-8"
              >
                No activity &mdash; system not yet active
              </TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}
