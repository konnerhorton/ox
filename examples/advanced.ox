# Advanced Training Log Example
# Demonstrates session RPE tracking with ACWR, monotony, and strain analysis
# ~8 weeks of realistic training data with sRPE, weigh-ins, notes, and queries

# Exercise Definitions
@exercise squat
equipment: barbell
tags: squat, lower
note: back squat, full depth
@end

@exercise deadlift
equipment: barbell
tags: hinge, lower
note: conventional barbell deadlift
@end

@exercise bench-press
equipment: barbell
tags: push, upper
note: flat barbell bench press
@end

@exercise kb-snatch
equipment: kettlebell
tags: power, full-body, unilateral
note: single-arm kettlebell snatch
@end

@exercise kb-oh-press
equipment: kettlebell
tags: push, upper, unilateral
note: single-arm overhead press
@end

@exercise kb-tgu
equipment: kettlebell
tags: full-body, unilateral
note: Turkish get-up
@end

@exercise kb-dh-swing
equipment: kettlebell
tags: hinge, lower, conditioning
note: double-handed kettlebell swing
@end

@exercise pullup
equipment: pull-up bar
tags: pull, upper
note: pronated grip pull-up
@end

@exercise goblet-squat
equipment: kettlebell
tags: squat, lower
note: weight held at chest
@end

@exercise burpee
equipment: none
tags: conditioning, full-body
note: chest to floor, explosive jump
@end

@exercise run
equipment: none
tags: cardio, conditioning
note: running for distance or time
@end

# Weigh-ins (morning, pre-training)
2025-01-06 W 165.2lb T07:00 "home"
2025-01-08 W 164.8lb T06:45 "home"
2025-01-13 W 165.0lb T07:00 "home"
2025-01-15 W 164.4lb T06:50 "home"
2025-01-20 W 164.6lb T07:10 "home"
2025-01-22 W 163.8lb T06:55 "home"
2025-01-27 W 164.2lb T07:00 "home"
2025-01-29 W 163.6lb T06:45 "home"
2025-02-03 W 163.4lb T07:00 "home"
2025-02-05 W 164.0lb T06:50 "home"
2025-02-10 W 163.8lb T07:05 "home"
2025-02-12 W 163.2lb T06:55 "home"
2025-02-17 W 163.0lb T07:00 "home"
2025-02-19 W 163.6lb T06:50 "home"
2025-02-24 W 164.4lb T07:00 "home"
2025-02-26 W 163.8lb T06:45 "home"

# Notes
2025-01-06 note "Starting 8-week block. Goal: build base, introduce sRPE tracking."
2025-01-27 note "Feeling good, ramping up intensity this week."
2025-02-03 note "Peak week incoming. Pushing volume and intensity."
2025-02-17 note "Deload week. Active recovery focus."
2025-02-24 note "Second peak block. Controlled spike for adaptation."

# Stored queries
2025-01-06 query "weekly-volume" "SELECT date(date, '-' || strftime('%w', date) || ' days') AS week, movement_name, ROUND(SUM(reps * weight_magnitude), 1) AS volume FROM training GROUP BY week, movement_name ORDER BY week, volume DESC"
2025-01-06 query "squat-progress" "SELECT date, weight_magnitude, weight_unit, reps, sets FROM training WHERE movement_name = 'squat' ORDER BY date"
2025-01-06 query "srpe-daily" "SELECT s.date, m.note FROM movements m JOIN sessions s ON m.session_id = s.id WHERE LOWER(m.name) = 'srpe' ORDER BY s.date"

# ============================================================================
# Week 1 - Base Building (low-moderate intensity)
# ============================================================================

@session
2025-01-06 * Lower Strength
srpe: "5; PT45M"
squat: 155lb 4x5
deadlift: 185lb 3x5
goblet-squat: 32kg 3x8
@end

@session
2025-01-07 * Upper KB
srpe: "4; PT35M"
kb-oh-press: 24kg 5x5
kb-snatch: 24kg 5x5
pullup: BW 4x8
@end

2025-01-08 * run: PT30M "easy pace, srpe: 3; PT30M"

@session
2025-01-09 * Lower Volume
srpe: "5; PT40M"
squat: 135lb 4x8
kb-dh-swing: 32kg 5x15
goblet-squat: 24kg 4x10
@end

@session
2025-01-10 * Upper Strength
srpe: "4; PT35M"
bench-press: 135lb 4x5
pullup: BW 5x5
kb-oh-press: 24kg 4x6
@end

# ============================================================================
# Week 2 - Base Building (slight progression)
# ============================================================================

@session
2025-01-13 * Lower Strength
srpe: "5; PT50M"
squat: 165lb 4x5
deadlift: 195lb 3x5
goblet-squat: 32kg 3x10
@end

@session
2025-01-14 * Upper KB
srpe: "5; PT40M"
kb-oh-press: 24kg 5x6
kb-snatch: 24kg 5x6
pullup: BW 4x8
kb-tgu: 24kg 3x1
@end

2025-01-15 * run: PT35M "moderate pace, srpe: 4; PT35M"

@session
2025-01-16 * Lower Volume
srpe: "5; PT45M"
squat: 145lb 4x8
kb-dh-swing: 32kg 5x15
goblet-squat: 32kg 4x10
@end

@session
2025-01-17 * Upper Strength
srpe: "5; PT40M"
bench-press: 140lb 4x5
pullup: BW 5x6
kb-oh-press: 24kg 5x6
@end

# ============================================================================
# Week 3 - Building (moderate intensity)
# ============================================================================

@session
2025-01-20 * Lower Strength
srpe: "6; PT50M"
squat: 175lb 4x5
deadlift: 205lb 3x5
goblet-squat: 32kg 4x10
@end

@session
2025-01-21 * Upper KB
srpe: "6; PT45M"
kb-oh-press: 32kg 5x4
kb-snatch: 24kg 6x6
pullup: BW 5x8
kb-tgu: 24kg 4x1
@end

2025-01-22 * run: PT40M "tempo intervals, srpe: 5; PT40M"

@session
2025-01-23 * Lower Volume
srpe: "6; PT50M"
squat: 155lb 5x8
kb-dh-swing: 32kg 6x15
goblet-squat: 32kg 5x10
@end

@session
2025-01-24 * Upper Strength + Conditioning
srpe: "6; PT50M"
bench-press: 150lb 4x5
pullup: 10lb 4x5
burpee: BW 5x10
@end

# ============================================================================
# Week 4 - Ramping Up (moderate-high)
# ============================================================================

@session
2025-01-27 * Lower Heavy
srpe: "7; PT55M"
squat: 185lb 5x5
deadlift: 225lb 3x5
goblet-squat: 32kg 4x10
@end

@session
2025-01-28 * Upper KB Heavy
srpe: "7; PT50M"
kb-oh-press: 32kg 5x5
kb-snatch: 32kg 5x4
pullup: 15lb 5x5
kb-tgu: 32kg 4x1
@end

2025-01-29 * run: PT35M "tempo, srpe: 5; PT35M"

@session
2025-01-30 * Lower Volume
srpe: "6; PT50M"
squat: 165lb 5x8
kb-dh-swing: 32kg 8x15
goblet-squat: 32kg 5x10
@end

@session
2025-01-31 * Full Body Power
srpe: "7; PT55M"
bench-press: 155lb 5x3
squat: 175lb 5x3
pullup: 20lb 4x3
@end

# ============================================================================
# Week 5 - Peak Week 1 (high intensity)
# ============================================================================

@session
2025-02-03 * Lower Max Effort
srpe: "8; PT60M"
squat: 205lb 5x3
deadlift: 245lb 3x3
goblet-squat: 32kg 3x8
@end

@session
2025-02-04 * Upper KB Volume
srpe: "7; PT55M"
kb-oh-press: 32kg 6x5
kb-snatch: 32kg 6x4
pullup: 20lb 5x5
kb-tgu: 32kg 5x1
@end

2025-02-05 * run: PT45M "long run with hills, srpe: 6; PT45M"

@session
2025-02-06 * Lower Hypertrophy
srpe: "7; PT55M"
squat: 175lb 5x8
kb-dh-swing: 32kg 8x20
burpee: BW 5x12
@end

@session
2025-02-07 * Upper Heavy
srpe: "8; PT60M"
bench-press: 165lb 5x5
pullup: 25lb 5x3
kb-oh-press: 32kg 5x5
@end

# ============================================================================
# Week 6 - Peak Week 2 (highest intensity)
# ============================================================================

@session
2025-02-10 * Lower Max Effort
srpe: "9; PT65M"
squat: 215lb 5x3
deadlift: 255lb 3x3
goblet-squat: 32kg 3x8
@end

@session
2025-02-11 * Upper KB Max
srpe: "8; PT55M"
kb-oh-press: 32kg 7x5
kb-snatch: 32kg 6x5
pullup: 25lb 5x4
kb-tgu: 32kg 5x1
@end

2025-02-12 * run: PT40M "tempo, srpe: 6; PT40M"

@session
2025-02-13 * Lower + Conditioning
srpe: "8; PT60M"
squat: 185lb 5x8
kb-dh-swing: 32kg 10x20
burpee: BW 8x10
@end

@session
2025-02-14 * Upper Heavy + Test
srpe: "9; PT60M"
bench-press: 175lb 5x3
pullup: 30lb 4x3
kb-oh-press: 32kg 6x5
@end

# ============================================================================
# Week 7 - Deload (low intensity, active recovery)
# ============================================================================

@session
2025-02-17 * Light Lower
srpe: "3; PT30M"
squat: 115lb 3x5
goblet-squat: 24kg 3x8
kb-dh-swing: 24kg 3x10
@end

@session
2025-02-18 * Light Upper
srpe: "3; PT25M"
bench-press: 95lb 3x5
pullup: BW 3x5
kb-oh-press: 24kg 3x5
@end

2025-02-19 * run: PT20M "easy, srpe: 2; PT20M"

@session
2025-02-20 * Light KB
srpe: "2; PT25M"
kb-tgu: 24kg 5x1
kb-snatch: 24kg 3x5
kb-dh-swing: 24kg 5x10
@end

# ============================================================================
# Week 8 - Rebuild (controlled spike for adaptation testing)
# ============================================================================

@session
2025-02-24 * Lower Strength
srpe: "7; PT55M"
squat: 185lb 5x5
deadlift: 225lb 4x3
goblet-squat: 32kg 4x10
@end

@session
2025-02-25 * Upper KB
srpe: "7; PT50M"
kb-oh-press: 32kg 6x5
kb-snatch: 32kg 5x5
pullup: 15lb 5x5
kb-tgu: 32kg 4x1
@end

2025-02-26 * run: PT40M "moderate, srpe: 5; PT40M"

@session
2025-02-27 * Lower Volume
srpe: "6; PT50M"
squat: 165lb 5x8
kb-dh-swing: 32kg 8x15
burpee: BW 5x10
@end

@session
2025-02-28 * Upper Heavy
srpe: "8; PT55M"
bench-press: 165lb 5x5
pullup: 25lb 4x4
kb-oh-press: 32kg 5x5
@end
