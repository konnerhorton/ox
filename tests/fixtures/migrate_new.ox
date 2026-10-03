# A representative slice of the old syntax, kept as a golden migration input.

@movement squat
equipment: barbell
tag: squat
note: back squat
@end

2025-01-05 T pullups: BW 5x10
2025-01-05 T run: 5km PT25M "easy pace"

@session
date: 2025-01-06
name: Lower Strength
srpe: 5 PT45M
squat: 155lb 4x5
deadlift: 185lb 3x5
note: "felt strong"
@end

@session
date: 2025-01-08
run: PT30M "easy pace"
srpe: 3 PT30M
@end

@session
date: 2025-01-09
name: Upper KB
srpe: 4 PT35M
kb-oh-press: 24kg 5x5
@end

@session
date: 2025-01-15
name: Planned Upper
completed: false
bench-press: 185lb 5x5
@end

2025-01-10 W 185lb T06:30 "home"
2025-01-10 note "deload week"
2025-01-10 query "recent" "SELECT * FROM training LIMIT 10"
