"""Hand-written standard plans, used when Gemini is unavailable.

They assume no religion or culture; the user can refine them once AI is back.
"""
from app.models import BudgetCategory, EventType, Idea, PlanSkeleton, Task, Vendor


def _skeleton(title, summary, categories, tasks, vendors, ideas) -> PlanSkeleton:
    return PlanSkeleton(
        title=title,
        summary=summary,
        budget_categories=[BudgetCategory(key=k, label=l, weight=w, essential=e) for k, l, w, e in categories],
        tasks=[Task(id=i, title=t, category_key=c, days_before=d) for i, t, c, d in tasks],
        vendors=[Vendor(category_key=c, role=r, questions_to_ask=q, book_by_days_before=d) for c, r, q, d in vendors],
        ideas=[Idea(title=t, description=d, kind=k) for t, d, k in ideas],
    )


_WEDDING = _skeleton(
    "Your wedding plan",
    "A standard wedding plan covering venue, food, decor, photography, attire and invitations. Refine it to match your customs.",
    [
        ("venue", "Venue", 22, True), ("catering", "Catering", 30, True), ("decor", "Decor & flowers", 12, False),
        ("photography", "Photography & video", 8, True), ("attire", "Attire & styling", 10, True),
        ("invitations", "Invitations", 3, False), ("entertainment", "Music & entertainment", 5, False),
        ("contingency", "Contingency", 10, True),
    ],
    [
        ("book-venue", "Shortlist and book the venue", "venue", 270),
        ("book-caterer", "Taste menus and book the caterer", "catering", 210),
        ("book-photographer", "Book the photographer and videographer", "photography", 180),
        ("plan-decor", "Finalise the decor theme and florist", "decor", 120),
        ("order-attire", "Order outfits and schedule fittings", "attire", 120),
        ("book-entertainment", "Book music or a DJ", "entertainment", 90),
        ("send-invitations", "Send invitations and track RSVPs", "invitations", 60),
        ("final-headcount", "Confirm the final headcount with the caterer", "catering", 10),
        ("final-fitting", "Final outfit fitting", "attire", 7),
        ("day-of-schedule", "Share the day-of schedule with vendors and family", "venue", 3),
        ("settle-payments", "Settle final vendor payments", "contingency", -3),
        ("thank-you-notes", "Send thank-you notes", "invitations", -14),
    ],
    [
        ("venue", "Venue manager", ["Is our date available?", "What is included in the hire?", "What are the cancellation terms?"], 240),
        ("catering", "Caterer", ["Can we book a tasting?", "What is the per-plate price?", "How do you handle dietary needs?"], 180),
        ("photography", "Photographer", ["Can we see full albums, not just highlights?", "When will we get the photos?"], 150),
        ("decor", "Decorator", ["Do you have photos of past setups?", "What does setup and teardown cost?"], 90),
    ],
    [
        ("Signature welcome drink", "Greet guests with a drink named after the couple.", "food"),
        ("Family portrait corner", "A lit backdrop where every family group gets a photo.", "activity"),
        ("Seasonal flower palette", "Build decor around flowers in season locally to save cost.", "decor"),
        ("Seed-paper favours", "Plantable seed-paper cards as a thank-you gift.", "favour"),
    ],
)

_BIRTHDAY = _skeleton(
    "Your birthday plan",
    "A standard birthday plan covering venue, cake and food, decor, entertainment and return gifts.",
    [
        ("venue", "Venue", 25, True), ("food-cake", "Food & cake", 35, True), ("decor", "Decor", 12, False),
        ("entertainment", "Entertainment", 15, False), ("invitations", "Invitations", 2, False),
        ("return-gifts", "Return gifts", 4, False), ("contingency", "Contingency", 7, True),
    ],
    [
        ("pick-theme", "Pick a theme and colour scheme", "decor", 40),
        ("book-venue", "Book the venue or prepare the space at home", "venue", 30),
        ("send-invites", "Send invitations", "invitations", 21),
        ("book-entertainment", "Book entertainment or plan games", "entertainment", 21),
        ("order-cake", "Order the cake", "food-cake", 10),
        ("buy-return-gifts", "Buy return gifts", "return-gifts", 7),
        ("confirm-headcount", "Confirm headcount and food quantities", "food-cake", 3),
        ("set-up-decor", "Set up the decorations", "decor", 0),
    ],
    [
        ("food-cake", "Baker", ["Can you match the theme?", "Do you offer eggless options?", "When is pickup or delivery?"], 14),
        ("entertainment", "Entertainer", ["What age group do you suit?", "How long is the show?"], 21),
    ],
    [
        ("Theme-matched cake", "A cake that echoes the party theme and colours.", "food"),
        ("DIY photo booth", "Props and a backdrop guests can use all evening.", "activity"),
        ("Balloon garland", "An organic balloon arch in the theme colours.", "decor"),
        ("Personalised return gifts", "Small gifts with each guest's name on them.", "favour"),
    ],
)

_COMMUNITY = _skeleton(
    "Your community event plan",
    "A standard community event plan covering permissions, sound, food, safety, publicity, volunteers and cleanup.",
    [
        ("venue-permits", "Venue & permissions", 20, True), ("sound-stage", "Sound & stage", 20, True),
        ("food-stalls", "Food & refreshments", 20, False), ("safety", "Safety & first aid", 8, True),
        ("publicity", "Publicity", 8, False), ("volunteers", "Volunteers & logistics", 8, True),
        ("cleanup", "Waste management", 6, True), ("contingency", "Contingency", 10, True),
    ],
    [
        ("form-committee", "Form an organising committee and assign roles", "volunteers", 90),
        ("police-permission", "Apply for police permission", "venue-permits", 60),
        ("municipal-permission", "Get municipal permission for the venue", "venue-permits", 60),
        ("find-sponsors", "Approach local sponsors", "publicity", 60),
        ("sound-permission", "Get sound permission and check time limits", "sound-stage", 45),
        ("book-sound-stage", "Book sound, lighting and stage", "sound-stage", 30),
        ("recruit-volunteers", "Recruit and brief volunteers", "volunteers", 21),
        ("publicise-event", "Publicise on posters, WhatsApp groups and social media", "publicity", 21),
        ("arrange-first-aid", "Arrange first aid, fire safety and emergency contacts", "safety", 14),
        ("plan-waste", "Plan waste segregation bins and a cleanup crew", "cleanup", 7),
        ("cleanup-day", "Clean up the venue and return borrowed items", "cleanup", -1),
        ("share-accounts", "Share accounts and photos with the community", "contingency", -7),
    ],
    [
        ("venue-permits", "Tent and venue supplier", ["Is the ground available on our date?", "Who handles setup?"], 45),
        ("sound-stage", "Sound and light vendor", ["Do you have a backup generator?", "Can you keep within sound limits?"], 30),
        ("food-stalls", "Food stall partner", ["Do you have a food safety licence?", "How do you handle waste?"], 21),
    ],
    [
        ("Local talent showcase", "Open the stage to schools and local artists.", "activity"),
        ("Zero-waste food stalls", "Steel plates and a washing station instead of disposables.", "food"),
        ("Volunteer badges", "Simple badges or caps so volunteers are easy to find.", "favour"),
        ("Community mural wall", "A wall where everyone adds a handprint or message.", "decor"),
    ],
)

_DEFAULTS: dict[str, PlanSkeleton] = {"wedding": _WEDDING, "birthday": _BIRTHDAY, "community": _COMMUNITY}


def default_skeleton(event_type: EventType) -> PlanSkeleton:
    return _DEFAULTS[event_type].model_copy(deep=True)
