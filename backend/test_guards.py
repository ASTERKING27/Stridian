"""
The guards on what goes into a student's record: run with  python test_guards.py
(no server needed — the same throwaway database as test_mobile_api.py).
"""

import sys
from types import SimpleNamespace as NS

import test_mobile_api as t     # sets up the throwaway database, and never sends a notification
from fastapi.testclient import TestClient

import sports_config as sc
import trainer

main, ok = t.main, t.ok


def run():
    codes = []
    main.mailer.send_code = lambda to, code: codes.append(code)
    with TestClient(main.app) as c:
        coach = ok(c.post("/api/auth/signup", json={"name": "R. Krishnan", "employee_id": "E1", "phone": "9444012345",
                                                    "email": "coach@x.in", "password": "coachpass1", "sport": "Football"}), 201)
        CH = {"Authorization": f"Bearer {coach['token']}"}
        ok(c.post("/api/student/code", json={"email": "a.m@srmist.edu.in"}), 202)
        tok = ok(c.post("/api/student/verify", json={"email": "a.m@srmist.edu.in", "code": codes[-1], "password": "studentpass1"}))["token"]
        SH = {"Authorization": f"Bearer {tok}"}
        sid = ok(c.post("/api/student/enrol", headers=SH, json={
            "enrol_code": ok(c.get("/api/enrol-code", headers=CH))["code"], "sport": "Football", "name": "Aarav Menon",
            "ra_number": "RA2211003010214", "dob": "2005-03-14", "phone": "9876543210", "father_name": "R",
            "mother_name": "L", "father_phone": "9876500000", "aadhaar": t.aadhaar("48211234567"),
            "blood_group": "B+", "category": "M"}), 201)["student"]["id"]
        url, raw = f"/api/students/{sid}/results", {**CH, "Content-Type": "application/json"}

        # only real numbers are stored: one NaN or infinity would break every report it is in
        for bad in (b'{"results": {"cmj": NaN}}', b'{"results": {"cmj": Infinity}}', b'{"results": {"cmj": "1e999"}}'):
            ok(c.put(url, headers=raw, content=bad), 400)
        for bad in (b"NaN", b"Infinity", b"-0.1"):
            ok(c.put("/api/sports/football/weights", headers=raw,
                     content=b'{"weights": {"Winger": {"sprint30m": %s}}}' % bad), 400)
        assert main.match_metrics.make_homography([[float("nan"), 0], [1, 0], [1, 1], [0, 1]],
                                                  [[0, 0], [1, 0], [1, 1], [0, 1]]) is None
        # and only possible ones
        for bad in ({"sprint30m": -520}, {"sprint30m": 0}, {"cmj": 99999}):
            ok(c.put(url, headers=CH, json={"results": bad}), 400)
        assert ok(c.get(f"/api/students/{sid}/history", headers=CH)) == []

        # a mistyped result can be taken back, and the one before it counts again
        ok(c.put(url, headers=CH, json={"results": {"sprint30m": 4.45}}))
        ok(c.put(url, headers=CH, json={"results": {"sprint30m": 44.5}}))      # unusual, but a coach may keep it
        slip = ok(c.get(f"/api/students/{sid}/history", headers=CH))[-1]
        assert slip["value"] == 44.5, slip
        ok(c.delete(f"{url}/{slip['id']}", headers=CH), 204)
        ok(c.delete(f"{url}/{slip['id']}", headers=CH), 404)
        assert ok(c.get(url, headers=CH))["results"] == {"sprint30m": 4.45}

        # a student's own clips are capped by the day
        clip = {"filename": "cmj.mp4", "size": 1024}
        for _ in range(main.STUDENT_CLIPS_PER_DAY):
            ok(c.post("/api/student/videos", headers=SH, json=clip), 201)
        ok(c.post("/api/student/videos", headers=SH, json=clip), 429)
        ok(c.post(f"/api/students/{sid}/videos", headers=CH, json=clip), 201)    # their coach still can

    # footage counts by how long they were tracked: ten seconds can't outvote three minutes
    here, there = NS(sport="Football"), NS(sport="Basketball")
    clips = [NS(metrics={"matchTopSpeed": 10.0}, context={"trackedSeconds": 10}, clip=here),
             NS(metrics={"matchTopSpeed": 2.0}, context={"trackedSeconds": 190}, clip=here),
             NS(metrics=None, context=None, clip=here),
             # ...and only in the sport they play now: a clip from one they have left says
             # nothing about this one, and this sport's coach couldn't open it to check
             NS(metrics={"matchTopSpeed": 9.0}, context={"trackedSeconds": 600}, clip=there)]
    assert main.match_values_of(NS(sport="Football", match_assignments=clips)) == {"matchTopSpeed": 2.4}

    # a clip its coach deletes while the worker is analysing it doesn't end the worker's
    # pass: the next clip in the queue is still analysed
    import worker
    with main.SessionLocal() as db:
        db.add_all(main.VideoAnalysis(student_id=sid, original_name=name, stored_name="k", status="queued")
                   for name in ("gone.mp4", "next.mp4"))
        db.commit()

    def analyse(db, job, tmp):
        if job.original_name == "gone.mp4":
            with main.SessionLocal() as coach_side:
                coach_side.delete(coach_side.get(main.VideoAnalysis, job.id))
                coach_side.commit()
            db.commit()
            raise RuntimeError("the clip is gone")
        job.status = "done"
        db.commit()

    worker.run_video = analyse
    worker.log.disabled = True       # the failure is the point; its traceback isn't
    with main.SessionLocal() as db:
        assert worker.work_queue(db, {"pose": True, "match": False}) == 2
        left = {v.original_name: v.status for v in db.scalars(main.select(main.VideoAnalysis))
                if v.original_name.endswith(("gone.mp4", "next.mp4"))}
        assert left == {"next.mp4": "done"}, left

    # training from weights saved before the match-card measures existed leaves those as they are
    live = sc.default_weights("Football")
    cards = {k for k, m in sc.metric_map("Football").items() if m["source"] == "card"}
    older = {p: {k: w for k, w in weights.items() if k not in cards} for p, weights in live.items()}
    learned = trainer.train("Football", older, live, [])["weights"]
    assert any(live[p].get(k) for p in live for k in cards)
    for position, weights in live.items():
        for key in cards:
            assert abs(learned[position][key] - weights.get(key, 0.0)) < 1e-3, (position, key)
    print("guards: ok")


if __name__ == "__main__":
    sys.exit(run())
