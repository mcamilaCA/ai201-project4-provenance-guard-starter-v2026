"""
What your test runs. ← UNIT 8, MILESTONE 3

Each of your five criteria needs something run against it. A criterion about
false positives needs your own writing. One about label coverage needs inputs
across the score range. One about the appeal path needs a real content_id.

Working that out is Milestone 3's first step, and this file is where you write
it down. `run_eval.py` runs everything here three times.

A scenario carries **either** of these:

    "texts"   a list of strings. Each is sent as {"text": ..., "creator_id": ...}
              with a creator_id made up for you. Use this for most criteria.

    "bodies"  a list of whole request bodies, sent exactly as written. Use this
              when the malformed request IS the point — empty text, no `text`
              field at all, something enormous. A bad-input criterion needs it,
              because you cannot express "the field is missing" as a string.

Coverage by criterion:

    1  own writing                                   (10 texts)
    2  clearly human + clearly AI                    (5 + 5 texts)
    3  label set: human / AI / borderline            (4 + 4 + 4 texts)
    4  appeal path                                   NOT here — needs a submission
                                                     first, then an appeal against
                                                     the returned content_id, so it
                                                     is tested separately.
    5  bad input                                     (4 bodies)

NOTE: every text below is a DRAFT. Criterion 1 especially must be replaced with
things you actually wrote yourself.
"""

SCENARIOS = [
    # ── Criterion 1: human writing is almost never labelled high-confidence AI ──
    {
        "name": "own writing",
        "criterion": 1,
        # Own writing from my field notes/poetry books.
        "texts": [
            " When looking at Mi Youren's painting and more so the mountains, we see a very pointed top, whereas when looking at Gao Kegong's painting and mountains, we see the rounded, and not axe-cut, brushstrokes. One can see how both paintings employ the voidness and blank space in the respective pieces. In the case of Mi Youren, we could feel the subtle balance brought about by leaving some blank space along the contours of mountains and trees. The painting assumes a mystically implicit quality since the translucent curtain is something that the user can interpret due to the use of the soft brush and white space. However, the blank space is used even more like a dreamland in Gao Kegong's painting, inviting the audience to imagine and meditate, and drown themselves within the painting as if it were another realm.",
            "As a computer science major, witnessing the city's recreation through technology and animation was particularly captivating. It made me realize how fictional things might look in history but how we have found proof of it as a reality. It showcased the intersection of fiction and reality in history, emphasizing how archaeological and technological realms can make the aspects of seemingly mythical tales based in reality more tangible.",
            "When enrolling in college classes, it can be difficult to find the best professor in your department, or the one that best fits your needs. Students can often waste a lot of time searching up each possible professor individually, and we wanted to create a way for this process to be easier and more efficient.",
            "We will be using Support Vector Machine (SVM). Some of the reasons why we will be using it are the multi-dimensional properties of our data, its flexibility for parameter tuning and how well it works even with imbalanced datasets. SVM works in an efficient manner when datasets have many factors that can alter outcome, such as the number of classes and different ratings of professors, moreover, when the dataset is not always balanced.",
            "By analysing propositions and deciphering their values AI can be able to solve bigger problems. It is the base needed for AI to determine “good” or “bad” in the same way humans learn good or bad when kids as foundation to deeper and more complex thought.",
            "In my opinion, to understand and comprehend something, you need to question, understand and interpret it; not to simply read the answer, but to get there on your own. That’s the beauty of it all. What you read today on questions of the past gives you the steps to understand the previous question and generate your own. Knowledge on top of knowledge, all held together by synapses.",
            "are people comfortable not being perfect around you? Meaning, are they not terrified by the idea of you correcting them and mocking them, or making them feel bad for not knowing something? I think the fact that they do, or don’t says a lot about a person, and we should pay attention to it more often…",
            "To be able to know your boundaries because of how deeply you understand yourself, that is one of the goals I am working on for the rest of the year (and highly likely some of the upcoming years too)",
            "I am a living controversy: so complicated yet so simple; sometimes committed to pure art and emotion, others embedded in systems and their workings; having a heart filled with passions and ambitious mindset, craving a soft life to balance it all. Why do we believe both sides can’t coexist, and who sold us that lie?",
            "Feeling stuck is a symptom of waiting for “something” to finally happen so you can do what you have in mind. The solution? Do what you have in mind. Take action, and movement will follow.",
        ],
    },

    # ── Criterion 2: clearly-AI and clearly-human text score far apart ──
    {
        "name": "clearly human",
        "criterion": 2,
        "texts": [
            "ugh don't even get me started on my landlord. he said he'd fix the heater \"this week\" three weeks ago. last night it was 52 degrees in my bedroom and i slept in a hoodie and two pairs of socks. my roommate thinks we should just buy a space heater and send him the bill lol. i'm tempted.",
            "Went to my cousin's wedding Saturday and the best moment was when the DJ's laptop crashed mid-song and my uncle just started singing to fill the gap. Off-key, loud, no shame. Everyone joined in by the second chorus. The cake was dry but nobody cared. I danced in my socks by the end.",
            "Quick update on the fence: the guy came, measured everything wrong, and then told me it was my fault for not marking the property line. So I'm out $200 and still have a gap where the gate goes. I'm calling someone else on Monday. Does anyone know a decent fence person near Dayton?",
            "When I was nine I broke my arm falling out of the apple tree behind our house. What I remember isn't the pain, it's that my dad carried me to the car and kept saying \"you're fine, you're fine\" in this very calm voice, and his hands were shaking the whole time. I only noticed years later.",
            "Look, I'm not saying the movie was bad, I'm saying it was two and a half hours long and about forty minutes of that was people staring out of windows. The cinematography was gorgeous, fine. But I checked my phone twice, and I never check my phone at the movies. Make of that what you will.",
        ],
    },
    {
        "name": "clearly AI",
        "criterion": 2,
        # Generic, polished, hedged, formulaic — the pattern most detectors key on.
        "texts": [
            "In today's fast-paced digital landscape, effective time management has become more important than ever. By prioritizing tasks, setting clear goals, and minimizing distractions, individuals can significantly enhance their productivity and achieve a healthier work-life balance. Furthermore, leveraging modern tools and techniques can streamline workflows and foster sustainable success in both personal and professional endeavors.",
            "Artificial intelligence is a transformative technology that is reshaping industries across the globe. From healthcare to finance, its applications are vast and varied. However, it is important to note that the adoption of AI also presents challenges, including ethical considerations and data privacy concerns. Ultimately, a balanced and thoughtful approach is essential to harness its full potential responsibly.",
            "Climate change represents one of the most pressing challenges of our time. Rising global temperatures, melting ice caps, and increasingly frequent extreme weather events underscore the urgent need for collective action. By adopting renewable energy sources, reducing carbon emissions, and promoting sustainable practices, we can work together to build a more resilient and environmentally conscious future for generations to come.",
            "Maintaining a healthy lifestyle involves a holistic approach that encompasses balanced nutrition, regular physical activity, adequate sleep, and effective stress management. It is essential to recognize that small, consistent changes can lead to significant long-term benefits. By cultivating mindful habits and seeking support when needed, individuals can improve their overall well-being and quality of life.",
            "Effective communication is a cornerstone of successful teamwork. It fosters trust, encourages collaboration, and ensures that all team members are aligned toward shared objectives. Moreover, active listening and constructive feedback play a vital role in resolving conflicts and driving innovation. In conclusion, organizations that prioritize clear communication are better positioned to thrive in an ever-evolving business environment.",
        ],
    },

    # ── Criterion 3: every label reachable, none dominates (12-text set) ──
    # Run these three scenarios together; the 12 results are tallied across them.
    {
        "name": "label set: human",
        "criterion": 3,
        "texts": [
            "my sister called at 11pm to tell me she got the job and i literally screamed into a pillow so i wouldn't wake the neighbours. we stayed on the phone for an hour just going over everything. she starts in three weeks, which is wild. i'm so proud of her i could cry, and also a little jealous, which i'm not going to mention.",
            "Not gonna lie, the hike was harder than the website made it sound. Two hours in, my friend Teo sat down on a rock and announced he was \"done with nature.\" We ate our sandwiches there, squashed flat in the bottom of his bag, and honestly they were the best sandwiches of my life. The view at the top was fine. The sandwiches were better.",
            "Update on the sourdough: it's alive!! After two failed attempts I finally got a starter that actually bubbles. I named her Doris. Baked my first loaf yesterday and it came out dense as a brick but the crust was crackly and my neighbour ate half of it standing in my kitchen, so I'm calling it a win.",
            "I keep rewriting the first paragraph of this essay and it keeps getting worse. Every version sounds like someone trying to sound smart. Maybe I should just say what happened: I failed the exam, I cried in the stairwell, and then I went and got fries. The rest of the essay is about what I learned. It's mostly about fries.",
        ],
    },
    {
        "name": "label set: AI",
        "criterion": 3,
        "texts": [
            "Sustainable urban development requires a comprehensive strategy that integrates efficient public transportation, green infrastructure, and community engagement. By investing in these areas, cities can reduce emissions, improve quality of life, and promote economic growth. It is crucial for policymakers to collaborate with stakeholders to ensure that development remains inclusive, equitable, and environmentally responsible.",
            "Remote work has fundamentally changed the modern workplace, offering flexibility and increased autonomy to employees. While it presents certain challenges, such as maintaining team cohesion and work-life boundaries, the benefits are substantial. Organizations that embrace hybrid models and invest in digital collaboration tools are well positioned to attract top talent and drive long-term success.",
            "Education plays a pivotal role in shaping individuals and societies. A well-rounded curriculum fosters critical thinking, creativity, and a lifelong love of learning. Moreover, the integration of technology in classrooms has opened new avenues for personalized instruction. As we look to the future, it is imperative to ensure equitable access to quality education for all learners.",
            "Cybersecurity has emerged as a critical priority for organizations of all sizes in the digital age. Threats such as phishing, ransomware, and data breaches can have devastating consequences. To mitigate these risks, businesses should implement robust security protocols, conduct regular employee training, and maintain up-to-date systems. A proactive approach is key to safeguarding sensitive information.",
        ],
    },
    {
        "name": "label set: borderline",
        "criterion": 3,
        # Formal-but-human prose, and human text that has been polished/hedged
        # until it sounds a bit like a model. Meant to land in the middle.
        "texts": [
            "The committee reviewed the proposal in detail and concluded that, while the budget is reasonable, the timeline appears optimistic given current staffing. We recommend a phased rollout beginning in the second quarter, with a formal review after ninety days. Should the initial phase meet its targets, the remaining work can proceed as originally planned.",
            "I believe remote work has real benefits, though it isn't for everyone. In my own experience I've saved about two hours a day on commuting, which I now spend on exercise and cooking. That said, I do miss the casual conversations in the office, and I sometimes find it hard to switch off in the evenings when my desk is ten feet from my couch.",
            "Over the past decade, the local library has become more than a place to borrow books. It now hosts job-skills workshops, language classes, and a weekly children's story hour. Residents I spoke with said the programs made them feel more connected to their neighbours, although several noted that funding for evening hours remains uncertain.",
            "When approaching a new codebase, I find it helpful to start with the tests rather than the source. They show what the authors thought was important, and they usually reveal how the pieces are meant to fit together. It isn't a perfect method, since some projects have poor coverage, but it has saved me a good deal of time on more than one occasion.",
        ],
    },

    # ── Criterion 5: bad input is handled explicitly ──
    {
        "name": "bad input",
        "criterion": 5,
        # Raw request bodies, sent exactly as written.
        # Expected: first three → HTTP 400, nothing stored.
        #           last        → HTTP 200 with a `warning` field + full analysis.
        "bodies": [
            {"creator_id": "eval_bad_missing"},                          # no text field
            {"text": "", "creator_id": "eval_bad_empty"},                # empty
            {"text": "   \n\t  ", "creator_id": "eval_bad_whitespace"},  # whitespace only
            {"text": "a" * 50001, "creator_id": "eval_bad_huge"},        # just over 50,000
        ],
    },

    # Criterion 4 (appeals) is intentionally absent: it needs a submission first
    # and then an appeal against the content_id that came back, which this file's
    # texts/bodies format can't express. Test it by hand or extend run_eval.py.
]


def validate() -> list[str]:
    """
    Complain about anything malformed, before a long run rather than during.

    A "bodies" scenario is deliberately exempt from the empty check — an empty
    string is the whole point of a bad-input case, and refusing to run one
    would make that criterion untestable.
    """
    problems = []
    for i, scenario in enumerate(SCENARIOS, 1):
        if not scenario.get("name"):
            problems.append(f"scenario {i} has no name")

        texts = scenario.get("texts")
        bodies = scenario.get("bodies")

        if texts and bodies:
            problems.append(
                f"scenario {i} ('{scenario.get('name')}') has both texts and "
                f"bodies — pick one"
            )
            continue

        if bodies:
            for j, body in enumerate(bodies, 1):
                if not isinstance(body, dict):
                    problems.append(
                        f"scenario {i}, body {j} is not a dict — bodies are whole "
                        f"request bodies, like {{'text': '', 'creator_id': 'x'}}"
                    )
            continue

        if not texts:
            problems.append(f"scenario {i} has no texts and no bodies")
            continue

        for j, text in enumerate(texts, 1):
            if not str(text).strip():
                problems.append(
                    f"scenario {i}, text {j} is empty — if an empty submission is what "
                    f"you're testing, use 'bodies' instead of 'texts'"
                )
            elif str(text).startswith("REPLACE ME"):
                problems.append(
                    f"scenario {i} ('{scenario.get('name')}'), text {j} is still "
                    f"the placeholder"
                )
    return problems
