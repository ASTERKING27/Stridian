import { useEffect, useState } from 'react'
import { api } from './api'
import { DetailsForm, shrinkImage } from './people'

/* Two users: a signed-in student enrolling themselves (their sport, the enrolment code
   their coach gave them, their details and a photo), or an admin adding someone by hand
   to the sport they are looking at. */
export default function StudentForm({ sports, coach, onSaved }) {
  const [enrolCode, setEnrolCode] = useState('')
  const [photo, setPhoto] = useState(null)          // { blob, url } — already shrunk
  const [photoError, setPhotoError] = useState('')
  const [round, setRound] = useState(0)             // a fresh form after each hand-added student
  const [added, setAdded] = useState('')

  useEffect(() => () => photo && URL.revokeObjectURL(photo.url), [photo])

  async function pickPhoto(e) {
    const file = e.target.files?.[0]
    setPhotoError('')
    if (!file) { setPhoto(null); return }
    try {
      const blob = await shrinkImage(file, 800, 0.88)
      setPhoto({ blob, url: URL.createObjectURL(blob) })
    } catch (err) {
      setPhotoError(err.message)
      e.target.value = ''
    }
  }

  async function submit(body) {
    if (!coach) {
      const me = await api.enrol({ ...body, enrol_code: enrolCode })
      // enrolled either way; a photo that didn't upload is asked for again on the dashboard
      try {
        me.student.photo_version = (await api.setMyPhoto(photo.blob)).photo_version
      } catch { /* shown as a to-do */ }
      onSaved(me)
      return null
    }
    const student = await api.createStudent(body)
    let note = ''
    if (photo) {
      try { await api.setStudentPhoto(student.id, photo.blob) } catch (err) { note = ` (photo not saved: ${err.message})` }
    }
    setAdded(`${student.name} added to ${student.sport}${note}. They won't have a login — students who enrol themselves do.`)
    setPhoto(null)
    setRound(r => r + 1)
    onSaved()
    return null
  }

  return (
    <>
      <div className="pagehead">
        <h1>{coach ? 'Add a student' : 'Enrol'}</h1>
        <p className="lede">
          {coach
            ? `For someone who can't enrol themselves, in ${coach.sport}. Students normally enrol on their own, with their university email and the coach's enrolment code.`
            : `Fill this in once — it becomes your record with the sports directorate. Your coach and the admins see it; nobody else does. Starred fields are needed.`}
        </p>
      </div>
      {added && <div className="banner">{added}</div>}

      <DetailsForm key={round} mode={coach ? 'create' : 'enrol'} sports={sports}
                   sport={coach?.sport} sportLocked={!!coach} onSubmit={submit}
                   submitLabel={coach ? 'Add student' : 'Enrol'}>
        <div className="card">
          <div className="card-head">
            <div>
              <h2>{coach ? 'Photo' : 'Your code and photo'}</h2>
              <p className="muted">
                {coach ? 'A clear, recent photo of their face, like a passport photo.'
                  : 'A clear, recent photo of your face, like a passport photo — it goes on your profile.'}
              </p>
            </div>
          </div>
          <div className="grid2">
            {!coach && (
              <div className="field">
                <label htmlFor="ecode">Enrolment code *</label>
                <input id="ecode" required autoComplete="off" value={enrolCode}
                       onChange={e => setEnrolCode(e.target.value)} />
                <p className="muted" style={{ marginTop: 5 }}>Your coach gives you this.</p>
              </div>
            )}
            <div className="field">
              <label htmlFor="photo">Photo{coach ? '' : ' *'}</label>
              <div className="row" style={{ flexWrap: 'nowrap' }}>
                {photo && <img className="photo" src={photo.url} alt="Your chosen photo" style={{ width: 56, height: 56 }} />}
                <input id="photo" type="file" accept="image/*" required={!coach} onChange={pickPhoto} />
              </div>
              {photoError && <div className="note err">{photoError}</div>}
            </div>
          </div>
        </div>
      </DetailsForm>
    </>
  )
}
