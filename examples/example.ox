# Training Log Example
# This file demonstrates the various formats and features
# Using a focused set of movements for better statistics

# Exercise Definitions
@movement squat
equipment: barbell
tag: squat
url: https://www.strongerbyscience.com/how-to-squat/
note: keep chest up, knees track over toes, full depth
@end

@movement deadlift
equipment: barbell
tag: hinge
url: https://www.strongerbyscience.com/how-to-deadlift/
note: neutral spine, drive through heels, hinge at hips
@end

@movement bench-press
equipment: barbell
tag: press
url: https://www.strongerbyscience.com/how-to-bench/
note: retract scapula, feet planted, bar path to mid-chest
@end

@movement overhead-press
equipment: barbell
tag: press
url: https://www.strongerbyscience.com/how-to-press/
note: brace core, vertical bar path, squeeze glutes
@end

@movement pullup
equipment: bodyweight
tag: pull
url: https://www.strongerbyscience.com/how-to-pull-up/
note: full hang to chin over bar, control descent
@end

@movement kb-swing
equipment: kettlebell
tag: hinge
url: https://www.strongfirst.com/the-swing/
note: explosive hip drive, park the bell, tight lats
@end

@movement kb-snatch
equipment: kettlebell
tag: ballistic
url: https://www.strongfirst.com/the-snatch/
note: punch through at top, smooth arc, tight shoulder
@end

@movement kb-clean-and-press
equipment: kettlebell
tag: combination
url: https://www.strongfirst.com/the-clean/
note: clean to rack position, press with full lockout
@end

@movement kb-turkish-getup
equipment: kettlebell
tag: getup
url: https://www.strongfirst.com/the-turkish-get-up/
note: eyes on bell, stable shoulder, controlled movement
@end

@movement box-jump
equipment: plyometric
tag: jump
url: https://www.bodybuilding.com/exercises/box-jump
note: soft landing, full hip extension, step down
@end

@movement burpee
equipment: bodyweight
tag: full-body
url: https://wodwell.com/exercise/burpee/
note: chest to floor, explosive jump, full extension
@end

@movement run
equipment: cardio
tag: endurance
url: https://www.runnersworld.com/training/
note: comfortable pace unless noted, focus on form
@end

@movement sprint
equipment: cardio
tag: speed
url: https://www.scienceforsport.com/sprint-training/
note: full recovery between efforts, quality over quantity
@end

@movement plank
equipment: bodyweight
tag: core
url: https://www.strongerbyscience.com/how-to-plank/
note: hold for time, ribs down, glutes squeezed
@end

@movement farmer-carry
equipment: kettlebell
tag: carry
url: https://www.strongfirst.com/the-farmer-carry/
note: carry for distance, tall posture, do not shrug
@end

# Week 1 - Strength Focus
@session
date: 2024-01-15
name: Lower Strength
squat: 185lb 5x5
deadlift: 225lb 3x5
box-jump: BW 3x5
@end

@session
date: 2024-01-16
name: Upper Strength
bench-press: 155lb 5x5
overhead-press: 95lb 3x8
pullup: BW 4x10
@end

@session
date: 2024-01-17
name: KB Workout
kb-swing: 32kg 5x15
kb-snatch: 24kg 5x5 "each arm"
kb-clean-and-press: 24kg 5x3 "each arm"
kb-turkish-getup: 24kg 5x1 "each arm"
@end

2024-01-18 T run: 5km PT30M "easy pace"

@session
date: 2024-01-19
name: Full Body
squat: 165lb 4x8
bench-press: 135lb 4x8
pullup: BW 4x8
kb-swing: 24kg 4x20
plank: BW PT45S 3x1
@end

2024-01-20 T run: 8km PT45M "long slow distance"

# Week 2 - Volume Phase
@session
date: 2024-01-22
name: Lower Volume
squat: 155lb 5x10
deadlift: 185lb 5x5
box-jump: BW 5x3
@end

@session
date: 2024-01-23
name: Upper Volume
bench-press: 135lb 5x10
overhead-press: 85lb 4x10
pullup: BW 5x8
@end

@session
date: 2024-01-24
name: Conditioning
burpee: BW 10x10
kb-swing: 32kg 10x15
box-jump: BW 10x5
plank: BW PT60S 3x1
@end

2024-01-25 T run: 4km PT25M

@session
date: 2024-01-26
name: KB Focus
kb-snatch: 24kg 8x5 "each arm"
kb-clean-and-press: 24kg 6x3 "each arm"
kb-turkish-getup: 24kg 6x1 "each arm"
kb-swing: 32kg 5x20
farmer-carry: 32kg 40m 4x1
@end

# Week 3 - Progressive Overload
@session
date: 2024-01-29
name: Lower Heavy
squat: 205lb 5x5
deadlift: 245lb 3x5
pullup: BW 4x8
@end

@session
date: 2024-01-30
name: Upper Heavy
bench-press: 165lb 5x5
overhead-press: 105lb 3x8
pullup: 25lb 4x5
@end

@session
date: 2024-01-31
name: KB & Conditioning
kb-swing: 32kg 8x15
kb-snatch: 24kg 6x5 "each arm"
burpee: BW 5x15
box-jump: BW 5x5
@end

2024-02-01 T run: PT35M

# Week 4 - Mixed Work
@session
date: 2024-02-02
name: Full Body Power
squat: 185lb 5x3
bench-press: 155lb 5x3
deadlift: 225lb 5x3
pullup: 20lb 4x5
@end

@session
date: 2024-02-03
name: KB Complex
kb-swing: 32kg 5x20
kb-clean-and-press: 32kg 5x3 "each arm"
kb-turkish-getup: 32kg 5x1 "each arm"
kb-snatch: 32kg 5x3 "each arm"
@end

2024-02-04 T run: 7km PT40M "tempo run"

@session
date: 2024-02-05
name: Circuit Training
burpee: BW 5x15
squat: 135lb 5x10
kb-swing: 24kg 5x20
box-jump: BW 5x8
plank: PT60S/PT45S/PT30S
@end

# Week 5 - Pyramid Work
@session
date: 2024-02-07
name: Lower Pyramid
squat: 135lb/155lb/175lb/195lb/175lb 5/5/5/3/5 "pyramid"
deadlift: 185lb/205lb/225lb 5/3/1
@end

@session
date: 2024-02-08
name: Upper Pyramid
bench-press: 135lb/145lb/155lb/165lb 5/5/3/1
overhead-press: 85lb/95lb/105lb 5/3/1
pullup: BW 5/5/5/5/5
@end

@session
date: 2024-02-09
name: KB Volume
kb-swing: 24kg 10x20 "every minute"
kb-snatch: 24kg 8x6 "each arm"
kb-clean-and-press: 24kg 6x5 "each arm"
@end

2024-02-10 T run: PT30M

# Week 6 - Deload
@session
date: 2024-02-12
name: Deload Lower
squat: 135lb 3x5 "deload week"
deadlift: 185lb 3x5
box-jump: BW 3x3
@end

@session
date: 2024-02-13
name: Deload Upper
bench-press: 115lb 3x5 "deload week"
overhead-press: 75lb 3x5
pullup: BW 3x5
@end

@session
date: 2024-02-14
name: Light KB
kb-swing: 24kg 5x15
kb-turkish-getup: 24kg 5x1 "each arm"
@end

2024-02-15 T run: 3km PT20M "easy"

# Week 7 - 5/3/1 Cycle 1 Week 1
@session
date: 2024-02-19
name: 5/3/1 Squat Day
note: "Cycle 1 Week 1"
squat: 155lb/175lb/195lb 5/5/8
pullup: BW 5x5
kb-swing: 32kg 3x20
@end

@session
date: 2024-02-20
name: 5/3/1 Bench Day
note: "Cycle 1 Week 1"
bench-press: 125lb/140lb/155lb 5/5/10
overhead-press: 85lb 4x8
@end

@session
date: 2024-02-21
name: 5/3/1 Deadlift Day
note: "Cycle 1 Week 1"
deadlift: 185lb/210lb/235lb 5/5/8
kb-swing: 32kg 5x15
@end

2024-02-22 T run: 6km PT35M

@session
date: 2024-02-23
name: KB & Plyometrics
kb-snatch: 24kg 6x5 "each arm"
kb-clean-and-press: 24kg 6x5 "each arm"
box-jump: BW 5x5
burpee: BW 5x10
@end

# Week 8 - 5/3/1 Cycle 1 Week 2
@session
date: 2024-02-26
name: 5/3/1 Squat Day
note: "Cycle 1 Week 2"
squat: 165lb/185lb/205lb 3/3/6
box-jump: BW 5x3
@end

@session
date: 2024-02-27
name: 5/3/1 Bench Day
note: "Cycle 1 Week 2"
bench-press: 135lb/150lb/165lb 3/3/8
pullup: BW 5x8
@end

@session
date: 2024-02-28
name: 5/3/1 Deadlift Day
note: "Cycle 1 Week 2"
deadlift: 200lb/225lb/250lb 3/3/7
kb-swing: 32kg 5x15
@end

2024-02-29 T run: PT40M

@session
date: 2024-03-01
name: KB Heavy
kb-swing: 32kg 8x15
kb-snatch: 32kg 5x3 "each arm"
kb-clean-and-press: 32kg 5x3 "each arm"
kb-turkish-getup: 32kg 5x1 "each arm"
@end

# Week 9 - 5/3/1 Cycle 1 Week 3
@session
date: 2024-03-04
name: 5/3/1 Squat Day
note: "Cycle 1 Week 3"
squat: 175lb/195lb/215lb 5/3/8
pullup: BW 4x8
@end

@session
date: 2024-03-05
name: 5/3/1 Bench Day
note: "Cycle 1 Week 3"
bench-press: 145lb/160lb/175lb 5/3/9
overhead-press: 95lb 4x8
@end

@session
date: 2024-03-06
name: 5/3/1 Deadlift Day
note: "Cycle 1 Week 3"
deadlift: 215lb/240lb/265lb 5/3/8 "grip was tough on the last set"
@end

2024-03-07 T run: 8km PT45M "felt strong"

@session
date: 2024-03-08
name: Conditioning
burpee: BW 8x12
kb-swing: 32kg 8x20
box-jump: BW 8x5
plank: 25lb PT45S 3x1 "plate on back"
@end

2024-03-09 T sprint: 100m 8x1 "track intervals, full recovery"

# Week 10 - 5/3/1 Cycle 1 Week 4 (Deload)
@session
date: 2024-03-11
name: 5/3/1 Squat Day
note: "Cycle 1 Week 4 - Deload"
squat: 105lb/120lb/135lb 3x5
box-jump: BW 3x3
@end

@session
date: 2024-03-12
name: 5/3/1 Bench Day
note: "Cycle 1 Week 4 - Deload"
bench-press: 85lb/95lb/110lb 3x5
pullup: BW 3x5
@end

@session
date: 2024-03-13
name: 5/3/1 Deadlift Day
note: "Cycle 1 Week 4 - Deload"
deadlift: 135lb/155lb/175lb 3x5
@end

2024-03-14 T run: PT25M "recovery pace"

@session
date: 2024-03-15
name: Light KB
kb-swing: 24kg 5x15
kb-turkish-getup: 24kg 5x1 "each arm"
@end

# Week 11 - 5/3/1 Cycle 2 Week 1
@session
date: 2024-03-18
name: 5/3/1 Squat Day
note: "Cycle 2 Week 1"
squat: 160lb/180lb/200lb 5/5/10
pullup: BW 5x5
@end

@session
date: 2024-03-19
name: 5/3/1 Bench Day
note: "Cycle 2 Week 1"
bench-press: 130lb/145lb/160lb 5/5/12
overhead-press: 90lb 5x8
@end

@session
date: 2024-03-20
name: 5/3/1 Deadlift Day
note: "Cycle 2 Week 1"
deadlift: 195lb/220lb/245lb 5/5/10
kb-swing: 32kg 5x20
@end

2024-03-21 T run: 5km PT30M

@session
date: 2024-03-22
name: KB Workout
kb-snatch: 24kg 8x6 "each arm"
kb-clean-and-press: 24kg 6x5 "each arm"
kb-turkish-getup: 24kg 6x1 "each arm"
burpee: BW 5x12
@end

# Week 12 - 5/3/1 Cycle 2 Week 2
@session
date: 2024-03-25
name: 5/3/1 Squat Day
note: "Cycle 2 Week 2"
squat: 170lb/190lb/210lb 3/3/8
box-jump: BW 5x3
@end

@session
date: 2024-03-26
name: 5/3/1 Bench Day
note: "Cycle 2 Week 2"
bench-press: 140lb/155lb/170lb 3/3/10
pullup: BW 5x8
@end

@session
date: 2024-03-27
name: 5/3/1 Deadlift Day
note: "Cycle 2 Week 2"
deadlift: 210lb/235lb/260lb 3/3/9
@end

2024-03-28 T run: PT40M

@session
date: 2024-03-29
name: Full Body Circuit
squat: 135lb 5x10
kb-swing: 32kg 5x20
burpee: BW 5x15
box-jump: BW 5x5
@end

# Week 13 - 5/3/1 Cycle 2 Week 3
@session
date: 2024-04-01
name: 5/3/1 Squat Day
note: "Cycle 2 Week 3"
squat: 180lb/200lb/220lb 5/3/10 "felt heavy but good"
pullup: BW 5x8
@end

@session
date: 2024-04-02
name: 5/3/1 Bench Day
note: "Cycle 2 Week 3"
bench-press: 150lb/165lb/180lb 5/3/11
overhead-press: 100lb 4x8
@end

@session
date: 2024-04-03
name: 5/3/1 Deadlift Day
note: "Cycle 2 Week 3"
deadlift: 225lb/250lb/275lb 5/3/10 "new rep PR!"
kb-swing: 32kg 5x20
@end

2024-04-04 T run: 6km PT35M

@session
date: 2024-04-05
name: KB & Plyometrics
kb-snatch: 32kg 5x4 "each arm"
kb-clean-and-press: 32kg 5x4 "each arm"
kb-turkish-getup: 32kg 5x1 "each arm"
box-jump: BW 5x5
farmer-carry: 32kg 40m/40m/30m/20m
@end

2024-04-06 T sprint: 100m/200m/400m "ladder"

# Week 14 - Bodyweight Focus
@session
date: 2024-04-08
name: Bodyweight Upper
pullup: BW 8x5
pullup: 25lb 5x3
bench-press: 135lb 3x8
overhead-press: 85lb 3x8
@end

@session
date: 2024-04-09
name: Bodyweight Lower
squat: BW 5x20
box-jump: BW 8x5
burpee: BW 5x20
@end

2024-04-10 T run: 9km PT50M "long run"

@session
date: 2024-04-11
name: KB Intensive
kb-swing: 32kg 10x20 "every 90 seconds"
kb-snatch: 24kg 8x6 "each arm"
kb-clean-and-press: 24kg 8x4 "each arm"
kb-turkish-getup: 24kg 8x1 "each arm"
farmer-carry: 40kg 30m 4x1
plank: BW PT90S 3x1
@end

@session
date: 2024-04-12
name: Power Work
squat: 185lb 6x3
deadlift: 225lb 6x3
box-jump: BW 6x3
@end

# Week 15 - Mixed Training
@session
date: 2024-04-15
name: Upper Power
bench-press: 120/130/140/150/175lb 5x3
overhead-press: 105lb 5x3
pullup: 30lb 5x3
@end

@session
date: 2024-04-16
name: Lower Power
squat: 205lb 5x3
deadlift: 245lb 5x3
box-jump: BW 5x3
@end

2024-04-17 T run: PT30M

@session
date: 2024-04-18
name: KB Complex
kb-swing: 32kg 8x15
kb-snatch: 24kg 6x6 "each arm"
kb-clean-and-press: 24kg 6x5 "each arm"
kb-turkish-getup: 24kg 6x1 "each arm"
@end

@session
date: 2024-04-19
name: Conditioning Circuit
burpee: BW 10x10
kb-swing: 24kg 10x20
box-jump: BW 10x5
@end

# Week 16 - Volume Block
@session
date: 2024-04-22
name: Lower Volume
squat: 165lb 5x10
deadlift: 205lb 5x8
kb-swing: 32kg 5x20
@end

@session
date: 2024-04-23
name: Upper Volume
bench-press: 145lb 5x10
overhead-press: 95lb 5x10
pullup: BW 5x10
@end

2024-04-24 T run: 8km PT45M

@session
date: 2024-04-25
name: KB & Bodyweight
kb-swing: 32kg 8x15
kb-snatch: 24kg 6x6 "each arm"
pullup: BW 5x8
burpee: BW 5x15
@end

@session
date: 2024-04-26
name: Full Body
squat: 175lb 4x8
bench-press: 155lb 4x8
deadlift: 215lb 4x5
pullup: BW 4x8
@end

# Week 17 - Strength Testing
@session
date: 2024-04-29
name: Squat Test
squat: 135lb/165lb/185lb/205lb/225lb/235lb 5/5/3/3/1/1 "new 1RM: 235lb"
box-jump: BW 3x3
@end

@session
date: 2024-04-30
name: Bench Test
bench-press: 115lb/135lb/155lb/175lb/185lb/190lb 5/5/3/3/1/1 "new 1RM: 190lb"
overhead-press: 95lb 3x5
pullup: BW 5x5
@end

@session
date: 2024-05-01
name: Deadlift Test
deadlift: 155lb/185lb/215lb/245lb/275lb/285lb 5/5/3/3/1/1 "new 1RM: 285lb"
kb-swing: 32kg 5x15
@end

2024-05-02 T run: 5km PT30M "recovery"

@session
date: 2024-05-03
name: KB Celebration
kb-snatch: 32kg 5x5 "each arm, felt great after PRs"
kb-clean-and-press: 32kg 5x5 "each arm"
kb-turkish-getup: 32kg 5x1 "each arm"
burpee: BW 5x10
@end

2024-05-03 note "started daily creatine ~5g"

2024-05-03 W 120lb "gym"
