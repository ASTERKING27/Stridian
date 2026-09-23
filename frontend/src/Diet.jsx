import { MacroBar } from './charts'

export default function Diet({ diet, name }) {
  if (!diet) return null

  if (!diet.available) {
    return (
      <div className="card">
        <div className="card-head"><div><h2>Diet plan</h2></div></div>
        <p className="empty"><b>Not enough to work from</b>{diet.reason}</p>
      </div>
    )
  }

  const t = diet.targets
  const parts = [
    { label: 'Carbohydrate', value: t.carbs_kcal, display: `${t.carbs_g} g`, color: 'var(--s1)' },
    { label: 'Protein', value: t.protein_kcal, display: `${t.protein_g} g`, color: 'var(--s2)' },
    { label: 'Fat', value: t.fat_kcal, display: `${t.fat_g} g`, color: 'var(--s3)' },
  ]

  return (
    <>
      <div className="card">
        <div className="card-head">
          <div>
            <h2>Daily fuelling targets</h2>
            <p className="muted">
              {diet.dietPreference} · {diet.style}-weighted sport
              {diet.allergies.length > 0 && ` · avoiding ${diet.allergies.join(', ')}`}
            </p>
          </div>
        </div>

        <div className="tiles" style={{ marginBottom: 18 }}>
          <div className="tile">
            <div className="k">Energy</div>
            <div className="v">{t.kcal.toLocaleString()}</div>
            <div className="s">kcal/day · {t.per_kg.kcal} per kg</div>
          </div>
          <div className="tile">
            <div className="k">Carbohydrate</div>
            <div className="v">{t.carbs_g} g</div>
            <div className="s">the main fuel</div>
          </div>
          <div className="tile">
            <div className="k">Protein</div>
            <div className="v">{t.protein_g} g</div>
            <div className="s">~{Math.round(t.protein_g / 4.5)} g per meal</div>
          </div>
          <div className="tile">
            <div className="k">Water</div>
            <div className="v">{(t.hydration_ml / 1000).toFixed(1)} L</div>
            <div className="s">plus 500–750 ml per extra hour</div>
          </div>
        </div>

        <h3>Where the energy comes from</h3>
        <MacroBar parts={parts} />
      </div>

      <div className="card">
        <div className="card-head">
          <div>
            <h2>A day of eating</h2>
            <p className="muted">
              Options already filtered for {name}&apos;s preferences. Pick one per slot.
            </p>
          </div>
        </div>

        <div className="grid3">
          {diet.meals.map(meal => (
            <div className="meal" key={meal.slot}>
              <h4>{meal.label}<span>{meal.kcal} kcal</span></h4>
              <ul>
                {meal.options.length === 0
                  ? <li className="muted">No option fits the current restrictions — plan this one manually.</li>
                  : meal.options.map(o => (
                      <li key={o.name}>{o.name} <em>· {o.tag}</em></li>
                    ))}
              </ul>
            </div>
          ))}
        </div>

        <h3 style={{ marginTop: 20 }}>How to use it</h3>
        <ul className="advice">
          {diet.notes.map((n, i) => <li key={i}>{n}</li>)}
        </ul>

        <div className="banner warn" style={{ marginTop: 16, marginBottom: 0 }}>
          {diet.disclaimer}
        </div>
      </div>
    </>
  )
}
