# Photos

Drop images here and run `python3 build.py --production`. Each photo slot on the site looks for a file named after the slot.

- `photos/placeholder/<name>.jpg`: a stand-in image. It is shown with a diagonal "PLACEHOLDER" watermark and a caption saying which real photo is still needed.
- `photos/<name>.jpg`: the final client photo. It is shown clean, with no watermark, and replaces any stand-in of the same name.

Use landscape images at least 1600 px wide (`.jpg`, `.jpeg`, `.webp` or `.png`). Only use images you have the right to publish.

| File name | Slot |
| --- | --- |
| `a-client-team-mid-activity-outdoors-faces-vi.jpg` | a client team mid-activity outdoors, faces visible and energetic (landscape, at least 1600 px wide) |
| `a-group-on-the-lawn-of-a-lakeside-resort.jpg` | a group on the lawn of a lakeside resort |
| `a-wellness-day-station-with-staff-taking-a-f.jpg` | a wellness day station with staff taking a fitness test |
| `article-image.jpg` | article image |
| `before-and-after-a-boardroom-stretch-session.jpg` | before and after a boardroom stretch session |
| `conference-hall-or-indoor-breakout-room.jpg` | conference hall or indoor breakout room |
| `facilitator-briefing-a-group-before-an-activ.jpg` | facilitator briefing a group before an activity |
| `indoor-problem-solving-challenge.jpg` | indoor problem-solving challenge |
| `rafting-team-at-sagana.jpg` | rafting team at Sagana |
| `rooms-or-dining-area.jpg` | rooms or dining area |
| `staff-in-an-office-car-park-doing-a-group-wo.jpg` | staff in an office car park doing a group workout |
| `team-member-portrait.jpg` | team member portrait |
| `the-crown-masters-team-together-smiling-at-a.jpg` | the Crown Masters team together, smiling, at a venue |
| `two-teams-competing-in-an-outdoor-challenge.jpg` | two teams competing in an outdoor challenge, wide shot showing the venue |
| `venue-lawn-or-main-activity-area.jpg` | venue lawn or main activity area |
| `year-end-group-photo-at-a-naivasha-resort.jpg` | year-end group photo at a Naivasha resort |

Sub-page hero slots follow the same rule: the file name is the slot caption in lower case with spaces replaced by hyphens, cut at 44 characters. Slots without a file keep the "Photo to supply" panel.
