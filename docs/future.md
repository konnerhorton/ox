# Updates

## Exercise definitions

I have many exercises list in the files, but none with real definitions.
This needs to be updated.
One thing that should be built in, unilateral exercises should implicitly mean both sides when reps are stated.
For example, `pistol-squat: 3x4` means I did 3 sets of 4 reps on _each_ leg.
For now, this will be captured with the work 'unilateral' in a `tag` in the definition

Id also like a way to query these meaningfully, maybe a plugin to pull up exercises with certain tags. Yeah thats it.

Plugin features:

- Show exercises with specific tags
- show most used exercises
- show least used
- show exercises that have not been done in a while, but were at one time popular

## Named sessions

A feature I would like eventually is to be able to track progression within a session (and provide the tooling for that tracking).
By that, I mean if I have a specific circuit I do, I want to see how my total volume or top weights have changed over time for that session.
To do that, we need named sessions, which we have.
And, some way to track exertion, which we can use [sRPE](#session-rate-of-perceived-scertion).
It would also be good to be able to categorize sessions based on their specific protocol ([protocol metadata](#protocol-metadata)), like emom, tababta, amrap, etc.
sRPE is definitely a priority between the two, as it is essential in tracking training load over time (without using a device like a heart-rate monitor).

Eventually, I need to build a plugin that allows me to compare across a single named session.
For a given alt-emom, I want to see how I have progressed over time, mainly based on total volume within the session (I typically do a 30min session).

## Session rate of perceived exertion

One of the goals of ox is simplicity and self awareness.
To that end, this is based around not really using devices like heart rate monitors etc.
All that you should need, if you need a device during your session at all, is a watch to keep the time.
Perhaps the most well established method of tracking training load through time in the literature is the session rate of perceived exertion.
With this tool, the individual rates their exertion over the session on some scale at some point after then session.
The most typical scale is 0-10 (foster modified borg scale, where the borg scale was originally developed for RPE).
And ratings are typically performed 30 minutes after the session.
The rating and total duration are multiplied to get some value that then can be compared across sessions.

For example:

A light run might take 30 minutes and feel like a 2 (easy): $2 \times 30min = 60 AU$
A 10-minute amrap crossfit session might by quick but feel like an 8 (two steps below maximal): $8 \times 10min = 80 AU$

Using these arbitrary units, I can then track total volume over whatever time period I am interested in.
Typically that will probably be weeks and months.

### implementation

The larger sessions, where I do emoms, barbell lifts, or bjj training are clear / obvious to use this with.
The smaller things though, like grip training, rehab work, etc. are more questionable.
For now, I will not include them, unless I do some max effort grip work (heavy hand etc.)

Syntax is the big question though, should I track these using first class citizens in `ox` or just use something like `spre: "4, PT30M"`
I'll do the above for now, until I figure out the path forward.

## cardio zones

similar to sRPE above, I'd like to track my cardio zones as well for specific runs (and maybe other modalities later on)
it would be the 1-5 system (don't know what it is call) but mostly using 2-5.
currently I have a `zone-2-run` movement, I could do that or have a note in the session, I'll stick with this for now.

For other levels, I'd like to do the norwegian 4x4 method for more vo2 max training, so that'd be zone 4 or 5.
Measures will be subjective since I do not have a heart rate monitor (and do not want to get one), but I think this will be sufficient.
I will also use the sRPE scores on these sessions because they will certainly need to be included in the calcs.
Honestly I probably wont be doing much / any zone 3 as the literature does not seem to suggest its that useful if you are doing a lot of zone 2 and sufficient amounts of 4/5.
I'd need to determine how Pavel sprints fit into this though, do they count as zone 4-5? THat implies VO2 max increase and I am not so sure that is the case

## protocol metadata

I'd like to add metadata to a session, both ad-hoc and standard session so I can know the full layout 3 years from now.
Items would include EMOM, AMRAP, Alt-EMOM, Tabata, RFT, Ladder, Complex, etc.
I would need some standard nomenclature to describe the scheme fully, though some would be implicit in the session movements.
And certain protocols will require certain metadata.
Alt-EMOM would require a list of movements and duration for set (if not a minute but say 30 seconds), duration would be derived later from the interval and total sets.

For now, since my sessions are quite simple, I will use `meta: "alt-emom, PT1M"`

There may need to be some provision for specifying target work/rest ratios, but that might get too verbose and could probably be handled with some text metadata instead of a proper data structure.

However this is defined, it should be once for the named session, in some sort of session ID data structure so that its not repeated everywhere the session is used.
