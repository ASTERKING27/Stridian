// The Coach Entry form's logic, checked without a browser:  npm run check
import assert from 'node:assert/strict'
import { changedResults, checkValue } from './src/api.js'

const sprint = { key: 'sprint30m', poor: 5.2, elite: 3.9, unit: 'sec' }
const cmj = { key: 'cmj', poor: 28, elite: 55, unit: 'cm' }
const trial = { key: 'timeTrial2km', poor: 600, elite: 450, unit: 'sec' }
const tests = [sprint, cmj, trial]

// only what the coach changed is sent: the saved numbers shown in the fields stay put
const shown = { sprint30m: '4.45', cmj: '36', timeTrial2km: '8:30' }
assert.deepEqual(changedResults(tests, shown, shown), {})
assert.deepEqual(changedResults(tests, { ...shown, sprint30m: '4,3', timeTrial2km: '8:10' }, shown),
                 { sprint30m: 4.3, timeTrial2km: 490 })
assert.deepEqual(changedResults(tests, { ...shown, cmj: '' }, shown), {})        // cleared: nothing new to save
assert.deepEqual(changedResults(tests, { cmj: '38' }, {}), { cmj: 38 })          // first results ever

// a number the test can't give is questioned, with the likely slip offered
assert.equal(checkValue(sprint, '4.45'), null)
assert.equal(checkValue(sprint, ''), null)
assert.equal(checkValue(trial, '8:30'), null)
assert.deepEqual(checkValue(sprint, '44.5'), { text: 'Usually between 2.34 and 8.32 sec.', fix: '4.45', range: true })
assert.equal(checkValue(cmj, '-5').fix, null)
for (const junk of ['abc', '1e999', '4.4.5']) assert.equal(checkValue(sprint, junk).text, 'That isn’t a number.')
assert.equal(checkValue(trial, 'eight').text, 'Type minutes and seconds, like 8:30.')
console.log('form: ok')
