import { View } from 'react-native'
import { router } from 'expo-router'
import { focusPosition } from '../lib/report'
import { useTheme } from '../lib/theme'
import { Bar, Eyebrow, H1, I, Icon, LinkRow, Mono, T } from '../ui'
import Field from './Field'

/* The front page of a report (Results board, 01): the position, its fit, where it plays,
   what else fits — then the pages behind it. `id` is set when a coach is looking. */
export default function ReportHome({ data, id, you = true }) {
  const { c } = useTheme()
  const pos = focusPosition(data)
  const rec = data.recommended
  const others = data.positions.filter(p => p.position !== pos.position && p.fit != null).slice(0, 2)
  const confirmed = data.student.status === 'verified' && data.student.verified_position === pos.position
  const open = page => router.push({ pathname: `/report/${page}`, params: id ? { id } : {} })
  const hasVideo = (data.videos ?? []).length > 0

  return (
    <>
      <View style={{ gap: 8 }}>
        <Eyebrow>{confirmed ? (you ? 'YOUR POSITION · CONFIRMED BY YOUR COACH' : 'POSITION · CONFIRMED') : you ? 'YOUR BEST POSITION' : 'BEST POSITION'}</Eyebrow>
        <View style={{ flexDirection: 'row', alignItems: 'flex-end', justifyContent: 'space-between', gap: 12 }}>
          <H1 size={34} style={{ flex: 1 }}>{pos.position}</H1>
          <View style={{ alignItems: 'flex-end', gap: 2 }}>
            <Mono size={30} font="monoMedium" style={{ lineHeight: 32 }}>{pos.fit == null ? '—' : Math.round(pos.fit)}</Mono>
            <Mono size={9.5} color="ink2" style={{ letterSpacing: 1.14 }}>FIT / 100</Mono>
          </View>
        </View>
        {!!pos.blurb && <T size={13.5} color="ink2" style={{ lineHeight: 19.5 }}>{pos.blurb}</T>}
        {pos.confidence === 'low' && (
          <Mono size={10.5} color="ink2" style={{ letterSpacing: 0.84 }}>LOW CONFIDENCE · FEW RESULTS BEHIND IT YET</Mono>
        )}
        {!!rec && rec.position !== pos.position && (
          <T size={13} color="ink2">By the numbers alone, {rec.position} fits best ({Math.round(rec.fit)}).</T>
        )}
      </View>

      <Field sport={data.sport} positions={data.positions.map(p => p.position)} best={pos.position}
             labelled={[pos.position, ...others.map(o => o.position)]} />

      {others.length > 0 && (
        <View>
          <Eyebrow style={{ paddingBottom: 8 }}>ALSO FITS</Eyebrow>
          {others.map(o => (
            <View key={o.position} style={{ flexDirection: 'row', alignItems: 'center', gap: 14, paddingVertical: 12,
                                             borderTopWidth: 1, borderTopColor: c.line }}>
              <T size={15} style={{ flex: 1 }}>{o.position}</T>
              <Bar value={o.fit / 100} w={90} />
              <Mono size={14} style={{ width: 26, textAlign: 'right' }}>{Math.round(o.fit)}</Mono>
            </View>
          ))}
        </View>
      )}

      <View>
        <Eyebrow style={{ paddingBottom: 4 }}>{you ? 'YOUR REPORT' : 'THE REPORT'}</Eyebrow>
        <LinkRow label={`Why ${pos.position}`} sub="Each measure, its weight and what it adds" onPress={() => open('why')} />
        <LinkRow label={you ? 'Your shape' : 'Their shape'} sub="Attributes, 0–100, against what the role leans on" onPress={() => open('shape')} />
        <LinkRow label="Levels" sub="University to International, measure by measure" onPress={() => open('levels')} />
        <LinkRow label="Every position" sub="All of them ranked, with what drove each" onPress={() => open('positions')} />
        <LinkRow label="Measurements" sub="Every result and its score" onPress={() => open('measurements')} />
        <LinkRow label="Training plan" sub={hasVideo ? 'From the tests and the video' : 'From the tests'} onPress={() => open('training')} />
        <LinkRow label="Diet" sub="Daily fuelling targets and a day of eating" onPress={() => open('diet')} />
        <LinkRow label="Drill videos" sub={hasVideo ? `${data.videos.length} clip${data.videos.length === 1 ? '' : 's'} · pose analysis` : 'Film a drill for pose analysis'}
                 onPress={() => router.push({ pathname: '/videos', params: id ? { id, name: data.student.name } : {} })} last />
      </View>
    </>
  )
}

// The report page before there is one (States board, 02).
export function ReportWaiting({ status }) {
  return (
    <>
      <View style={{ gap: 8 }}>
        <Eyebrow>MY REPORT</Eyebrow>
        <T font="medium" size={26} style={{ lineHeight: 31 }}>
          Your coach hasn’t verified you yet. Once they log your tests, your full breakdown unlocks right here.
        </T>
      </View>
      <Steps steps={[
        ['You enrolled with the squad code', 'done'],
        ['Your coach verifies your position', status === 'verified' ? 'done' : 'now'],
        ['Your first tests are logged', 'later'],
      ]} />
    </>
  )
}

function Steps({ steps }) {
  return (
    <View>
      <Eyebrow style={{ paddingBottom: 6 }}>WHAT HAPPENS NEXT</Eyebrow>
      {steps.map(([text, state]) => <Step key={text} text={text} state={state} />)}
    </View>
  )
}

function Step({ text, state }) {
  const { c } = useTheme()
  const box = { width: 22, height: 22, alignItems: 'center', justifyContent: 'center' }
  return (
    <View style={{ flexDirection: 'row', alignItems: 'center', gap: 12, paddingVertical: 11, borderTopWidth: 1, borderTopColor: c.line }}>
      {state === 'done' && <View style={[box, { backgroundColor: c.ink }]}><Icon d={I.check} size={14} sw={2} color={c.bg} /></View>}
      {state === 'now' && <View style={[box, { borderWidth: 1.5, borderColor: c.ink }]} />}
      {state === 'later' && <View style={[box, { borderWidth: 1, borderColor: c.ink2, borderStyle: 'dashed' }]} />}
      <T size={14.5} color={state === 'later' ? 'ink2' : 'ink'} style={{ flex: 1 }}>{text}</T>
      {state === 'now' && <Mono size={10} color="ink2" style={{ letterSpacing: 0.8 }}>WAITING</Mono>}
    </View>
  )
}
