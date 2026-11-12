STRIDIAN — DESIGN FILES AND CODE

boards/   Every board on the design canvas, as its final source (.dc.html),
          plus canvas.json (which board sits on which page, and where).
          View them on the canvas link — they need the canvas to display.

code/     The scripts that generated the boards.
  build.py          shared style kit: colours, fonts, phone frame, buttons
  icons.py          the icon set (sports + UI), 24 x 24 stroke paths
  logo7.py          builds the S-runner logo outline (current version)
  logo6.py, ascii.py  earlier logo step and a text preview of the shape
  gen.py            computes each sport's positions, metrics and fit scores
                    from backend/sports_config.py (run from the repo root)
  sports.json       its output, used by the Results board
  Results.tpl.html  Results board template (sports.json is inserted into it)
  haptics_data.py   every haptic pattern, timing and placement
  b_*.py            one script per board group:
                      b_upload   video upload and processing
                      b_pose     pose overlay
                      b_coach    coach screens
                      b_onboard  onboarding and sign in
                      b_states   empty, loading, error and streak states
                      b_profile  profile and settings
                      b_feedback button states and confirmations
                      b_motion   reduced motion
                      b_icons    icon set
                      b_haptics  both haptics plans

The first boards (logo, launch, tab change, tab bar, template, pull to
refresh, level reached, badges, logo options) were written by hand — their
code is the .dc.html file itself in boards/.

To rebuild a board: python3 code/b_upload.py (and so on). Each script
writes into a folder called stridian/project inside code/ — create it first.
