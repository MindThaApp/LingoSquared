from sqlalchemy import select
from app.db.session import SessionLocal
from app.models import Language, Achievement
from app.schemas.api import ImportRequest
from app.content.service import import_content

LANGUAGES=[("en","English","English","latin","ltr"),("nl","Dutch","Nederlands","latin","ltr"),("fr","French","Français","latin","ltr"),("de","German","Deutsch","latin","ltr"),("it","Italian","Italiano","latin","ltr"),("es","Spanish","Español","latin","ltr"),("ru","Russian","Русский","cyrillic","ltr"),("zh","Chinese (Mandarin, Simplified)","简体中文","han","ltr"),("fa","Farsi","فارسی","arabic","rtl"),("prs","Dari","دری","arabic","rtl"),("pl","Polish","Polski","latin","ltr"),("ro","Romanian","Română","latin","ltr"),("hi","Hindi","हिन्दी","devanagari","ltr")]

def block(text,language_code):
    return {"text":text,"language_code":language_code,"direction":"rtl" if language_code in {"fa","prs"} else "ltr"}

def teach(kind,target,target_code,translation,source_code,title=None,note=None):
    return {"kind":kind,"title":title,"text_blocks":[block(target,target_code),block(translation,source_code)],"note":note}

FARSI={
    "source_language":"en","target_language":"fa","title":"Farsi Foundations","description":"Original beginner material for everyday introductions and courtesy.","level":"A1",
    "units":[
        {"title":"Greetings and introductions","order":1,"section":"reading_writing","lessons":[
            {"title":"Hello and goodbye","order":1,"teaching":[
                teach("vocabulary","سلام","fa","hello","en"),teach("vocabulary","ممنون","fa","thank you","en"),teach("vocabulary","خداحافظ","fa","goodbye","en"),teach("phrase","من سارا هستم","fa","I am Sara","en",note="هستم is the first-person form of ‘to be’."),
            ],"exercises":[
                {"type":"multiple_choice","order":1,"prompt":{"text_blocks":[block("Choose the Farsi word for hello.","en")],"options":["سلام","خداحافظ","ممنون"]},"correct_response":"سلام","feedback":"سلام (salâm) is a common greeting.","xp":10},
                {"type":"translation","order":2,"prompt":{"text_blocks":[block("Thank you","en")]},"correct_response":"ممنون","feedback":"ممنون means thank you.","xp":10},
                {"type":"word_order","order":3,"prompt":{"text_blocks":[block("Arrange: I am Sara.","en")],"word_bank":["من","سارا","هستم"]},"correct_response":["من","سارا","هستم"],"xp":10},
            ]},
            {"title":"Meeting someone","order":2,"teaching":[
                teach("phrase","حال شما چطور است؟","fa","How are you?","en"),teach("phrase","من رامین هستم","fa","I am Ramin","en"),teach("vocabulary","خداحافظ","fa","goodbye","en"),
            ],"exercises":[
                {"type":"reverse_translation","order":1,"prompt":{"text_blocks":[block("حال شما چطور است؟","fa")]},"correct_response":"How are you?","xp":10},
                {"type":"fill_in_blank","order":2,"prompt":{"text_blocks":[block("من ___ هستم","fa")]},"correct_response":"رامین","feedback":"Insert the taught name in the blank.","xp":10},
                {"type":"flashcard","order":3,"prompt":{"text_blocks":[block("خداحافظ","fa")],"back_text_blocks":[block("goodbye","en")]},"correct_response":"goodbye","xp":10},
            ]},
        ]},
        {"title":"Reading and sentence building","order":2,"section":"reading_writing","lessons":[
            {"title":"A short introduction","order":1,"teaching":[
                teach("phrase","سلام، من سارا هستم.","fa","Hello, I am Sara.","en"),
                teach("grammar_note","من سارا هستم","fa","I am Sara","en","The first-person copula", "In this pattern, هستم supplies ‘am’ at the end of the sentence."),
            ],"exercises":[
                {"type":"grammar_check","order":1,"prompt":{"text_blocks":[block("Is this taught sentence grammatically complete?","en"),block("من سارا هستم","fa")],"options":["yes","no"]},"correct_response":"yes","feedback":"The pronoun, name, and copula form a complete sentence.","xp":10},
                {"type":"reading_comprehension","order":2,"prompt":{"text_blocks":[block("سلام، من سارا هستم.","fa"),block("What is the speaker's name?","en")],"options":["Sara","Mina","Ramin"]},"correct_response":"Sara","xp":10},
                {"type":"writing_prompt","order":3,"prompt":{"text_blocks":[block("Write the sentence you learned: I am Sara.","en")]},"correct_response":"من سارا هستم","feedback":"The taught answer is: من سارا هستم","xp":10},
            ]},
        ]},
        {"title":"Guided speaking","order":3,"section":"speaking","lessons":[
            {"title":"First conversation","order":1,"teaching":[
                teach("dialogue","سلام! حال شما چطور است؟","fa","Hello! How are you?","en"),teach("dialogue","خوب هستم، ممنون","fa","I am well, thank you","en"),teach("pronunciation_note","سلام","fa","hello","en",note="The long â in salâm is sustained."),
            ],"exercises":[
                {"type":"dialogue_response","order":1,"prompt":{"text_blocks":[block("سلام! حال شما چطور است؟","fa"),block("Use the reply you just learned.","en")]},"correct_response":"خوب هستم، ممنون","feedback":"خوب هستم، ممنون means I am well, thank you.","xp":10},
                {"type":"speaking_placeholder","order":2,"prompt":{"text_blocks":[block("Say سلام aloud.","en")]},"correct_response":"سلام","feedback":"Speech recognition is coming soon.","xp":0},
            ]},
        ]},
    ],
    "content_items":[
        {"kind":"vocabulary","language_code":"fa","title":"Core greetings","content":{"entries":[{"term":"سلام","meaning":"hello"},{"term":"ممنون","meaning":"thank you"},{"term":"خداحافظ","meaning":"goodbye"}]}},
        {"kind":"phrase","language_code":"fa","title":"Introductions","content":{"text":"من سارا هستم","translation":"I am Sara"}},
        {"kind":"grammar_note","language_code":"fa","title":"Copula","content":{"body":"هستم is the first-person singular form of ‘to be’."}},
    ],
}

EN_TO_DARI={
    "source_language":"en","target_language":"prs","title":"Dari Foundations","description":"A short original introduction to common Dari greetings and introductions.","level":"A1",
    "units":[{"title":"Greetings and introductions","order":1,"section":"reading_writing","lessons":[
        {"title":"Everyday greetings","order":1,"teaching":[
            teach("vocabulary","سلام","prs","hello","en"),teach("vocabulary","تشکر","prs","thank you","en",note="تشکر is a common Dari expression of thanks."),teach("phrase","خدا حافظ","prs","goodbye","en"),
        ],"exercises":[
            {"type":"multiple_choice","order":1,"prompt":{"text_blocks":[block("Choose the Dari word for thank you.","en")],"options":["تشکر","سلام","خدا حافظ"]},"correct_response":"تشکر","xp":10},
            {"type":"translation","order":2,"prompt":{"text_blocks":[block("Goodbye","en")]},"correct_response":"خدا حافظ","xp":10},
            {"type":"flashcard","order":3,"prompt":{"text_blocks":[block("سلام","prs")],"back_text_blocks":[block("hello","en")]},"correct_response":"hello","xp":10},
        ]},
        {"title":"Introduce yourself","order":2,"teaching":[
            teach("phrase","نام من احمد است","prs","My name is Ahmad","en"),teach("phrase","حال شما چطور است؟","prs","How are you?","en"),teach("phrase","خوب هستم، تشکر","prs","I am well, thank you","en",note="هستم expresses ‘I am’ in this response."),
        ],"exercises":[
            {"type":"word_order","order":1,"prompt":{"text_blocks":[block("Arrange the Dari sentence: My name is Ahmad.","en")],"word_bank":["نام","من","احمد","است"]},"correct_response":["نام","من","احمد","است"],"xp":10},
            {"type":"reverse_translation","order":2,"prompt":{"text_blocks":[block("حال شما چطور است؟","prs")]},"correct_response":"How are you?","xp":10},
            {"type":"dialogue_response","order":3,"prompt":{"text_blocks":[block("حال شما چطور است؟","prs"),block("Reply with the phrase you learned.","en")]},"correct_response":"خوب هستم، تشکر","xp":10},
        ]},
    ]}],
    "content_items":[{"kind":"vocabulary","language_code":"prs","title":"Dari greetings","content":{"entries":[{"term":"سلام","meaning":"hello"},{"term":"تشکر","meaning":"thank you"},{"term":"خدا حافظ","meaning":"goodbye"}]}}],
}

DARI_TO_EN={
    "source_language":"prs","target_language":"en","title":"English Foundations for Dari Speakers","description":"A short English course explained through common Dari equivalents.","level":"A1",
    "units":[{"title":"سلام‌ها و معرفی","order":1,"section":"reading_writing","lessons":[
        {"title":"Hello and courtesy","order":1,"teaching":[
            teach("vocabulary","hello","en","سلام","prs"),teach("phrase","thank you","en","تشکر","prs"),teach("phrase","goodbye","en","خدا حافظ","prs"),
        ],"exercises":[
            {"type":"multiple_choice","order":1,"prompt":{"text_blocks":[block("واژۀ انگلیسی برای «تشکر» را انتخاب کنید.","prs")],"options":["thank you","hello","goodbye"]},"correct_response":"thank you","xp":10},
            {"type":"translation","order":2,"prompt":{"text_blocks":[block("سلام","prs")]},"correct_response":"hello","xp":10},
            {"type":"flashcard","order":3,"prompt":{"text_blocks":[block("goodbye","en")],"back_text_blocks":[block("خدا حافظ","prs")]},"correct_response":"خدا حافظ","xp":10},
        ]},
        {"title":"Introducing yourself","order":2,"teaching":[
            teach("phrase","My name is Ahmad.","en","نام من احمد است.","prs"),teach("phrase","How are you?","en","حال شما چطور است؟","prs"),teach("phrase","I am well, thank you.","en","خوب هستم، تشکر.","prs"),
        ],"exercises":[
            {"type":"word_order","order":1,"prompt":{"text_blocks":[block("جملهٔ انگلیسی «نام من احمد است» را مرتب کنید.","prs")],"word_bank":["My","name","is","Ahmad."]},"correct_response":["My","name","is","Ahmad."],"xp":10},
            {"type":"reverse_translation","order":2,"prompt":{"text_blocks":[block("How are you?","en")]},"correct_response":"حال شما چطور است؟","xp":10},
            {"type":"writing_prompt","order":3,"prompt":{"text_blocks":[block("به انگلیسی بنویسید: خوب هستم، تشکر.","prs")]},"correct_response":"I am well, thank you.","xp":10},
        ]},
    ]}],
    "content_items":[{"kind":"phrase","language_code":"en","title":"English introductions","content":{"entries":[{"text":"My name is Ahmad.","meaning":"نام من احمد است."}]}}],
}

DARI_A2={
    "source_language":"en","target_language":"prs","title":"Dari Elementary","description":"A2 practice with short connected plans, times, and polite requests.","level":"A2",
    "units":[{"title":"Plans and practical requests","order":1,"section":"reading_writing","lessons":[
        {"title":"Talking about today's plans","order":1,"teaching":[
            teach("phrase","امروز می‌خواهم به بازار بروم.","prs","Today I want to go to the market.","en",note="می‌خواهم introduces something the speaker wants or intends to do."),
            teach("phrase","بعد از کار با دوستم دیدار می‌کنم.","prs","After work, I meet my friend.","en"),
            teach("phrase","ساعت سه حرکت می‌کنیم.","prs","We leave at three o’clock.","en"),
        ],"exercises":[
            {"type":"reading_comprehension","order":1,"prompt":{"text_blocks":[block("امروز می‌خواهم به بازار بروم. بعد از کار با دوستم دیدار می‌کنم.","prs"),block("Where does the speaker intend to go today?","en")],"options":["the market","the station","the school"]},"correct_response":"the market","xp":10},
            {"type":"translation","order":2,"prompt":{"text_blocks":[block("We leave at three o’clock.","en")]},"correct_response":"ساعت سه حرکت می‌کنیم.","xp":10},
            {"type":"word_order","order":3,"prompt":{"text_blocks":[block("Arrange the sentence: After work, I meet my friend.","en")],"word_bank":["بعد","از","کار","با","دوستم","دیدار","می‌کنم"]},"correct_response":["بعد","از","کار","با","دوستم","دیدار","می‌کنم"],"xp":10},
        ]},
        {"title":"Asking for help and directions","order":2,"teaching":[
            teach("phrase","آیا می‌توانید به من کمک کنید؟","prs","Can you help me?","en",note="می‌توانید is a polite way to ask whether someone can do something."),
            teach("phrase","بلی، البته.","prs","Yes, of course.","en"),
            teach("phrase","ایستگاه بس کجاست؟","prs","Where is the bus stop?","en",note="بس is the common Afghan Dari word for bus."),
        ],"exercises":[
            {"type":"dialogue_response","order":1,"prompt":{"text_blocks":[block("آیا می‌توانید به من کمک کنید؟","prs"),block("Reply with the polite agreement you learned.","en")]},"correct_response":"بلی، البته.","xp":10},
            {"type":"reverse_translation","order":2,"prompt":{"text_blocks":[block("ایستگاه بس کجاست؟","prs")]},"correct_response":"Where is the bus stop?","xp":10},
            {"type":"writing_prompt","order":3,"prompt":{"text_blocks":[block("Write the polite Dari question: Can you help me?","en")]},"correct_response":"آیا می‌توانید به من کمک کنید؟","xp":10},
        ]},
    ]}],
    "content_items":[{"kind":"phrase","language_code":"prs","title":"Plans and requests","content":{"entries":[{"text":"امروز می‌خواهم به بازار بروم.","meaning":"Today I want to go to the market."},{"text":"آیا می‌توانید به من کمک کنید؟","meaning":"Can you help me?"}]}}],
}

COURSE={"courses":[FARSI,EN_TO_DARI,DARI_TO_EN,DARI_A2]}

def main():
    with SessionLocal() as db:
        for code,name,native,script,direction in LANGUAGES:
            if not db.get(Language,code): db.add(Language(code=code,name=name,native_name=native,script=script,direction=direction))
        for code,title,description,threshold in [("first_steps","First Steps","Earn your first XP.",1),("xp_100","Century","Earn 100 XP.",100)]:
            if not db.scalar(select(Achievement).where(Achievement.code==code)): db.add(Achievement(code=code,title=title,description=description,threshold=threshold))
        db.commit(); count,errors,counters=import_content(db,ImportRequest.model_validate(COURSE))
        if errors and not counters: raise RuntimeError(errors)
        print(f"Seeded 10 languages and {count} courses.")

if __name__=="__main__": main()
