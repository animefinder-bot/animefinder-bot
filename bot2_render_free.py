import random
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import httpx

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)


# =========================
# SETTINGS
# =========================

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is not set.")

ANILIST_URL = "https://graphql.anilist.co"


# =========================
# MAIN MENU
# =========================

def home_keyboard():
    keyboard = [
        ["🔥 Trending Anime", "⭐ Best Anime"],
        ["🇨🇳 Best Donghua", "🎭 Genres"],
        ["🔎 Search", "🎯 Random Anime"],
        ["❤️ Favorites", "📊 Top Rated"],
        ["🆕 Recently Released", "📺 Where to Watch"],
        ["💡 Recommendations", "⚙️ Settings"],
    ]

    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True
    )


# =========================
# START
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    context.user_data["search_mode"] = False

    await update.message.reply_text(
        "👋 <b>Anime & Donghua Finder</b>\n\n"
        "Anime search aur discovery ke liye bot mein welcome! 🎬\n\n"
        "Neeche menu se option choose karo.",
        parse_mode="HTML",
        reply_markup=home_keyboard()
    )


# =========================
# ANILIST REQUEST
# =========================

async def anilist_request(query, variables=None):

    async with httpx.AsyncClient(timeout=25) as client:

        response = await client.post(
            ANILIST_URL,
            json={
                "query": query,
                "variables": variables or {}
            }
        )

    print("AniList Status:", response.status_code)

    if response.status_code != 200:
        print("AniList Response:", response.text)
        return None

    data = response.json()

    if "errors" in data:
        print("GraphQL Error:", data["errors"])
        return None

    return data


# =========================
# SEARCH ANIME
# =========================

async def search_anime(update, context):

    if not context.user_data.get("search_mode"):
        return

    anime_name = update.message.text.strip()

    if not anime_name:
        return

    await update.message.reply_text(
        "🔎 Anime search ho raha hai..."
    )

    query = """
    query ($search: String) {

        Page(page: 1, perPage: 10) {

            media(
                search: $search,
                type: ANIME,
                isAdult: false
            ) {

                id

                title {
                    romaji
                    english
                }

                startDate {
                    year
                }

                episodes

                averageScore

                status

                genres

                description(asHtml: false)

                coverImage {
                    large
                }

                siteUrl

                externalLinks {
                    site
                    url
                }
            }
        }
    }
    """

    data = await anilist_request(
        query,
        {
            "search": anime_name
        }
    )

    if not data:

        await update.message.reply_text(
            "❌ Anime database se response nahi mila.\n"
            "Thodi der baad try karo."
        )

        context.user_data["search_mode"] = False
        return

    anime_list = data["data"]["Page"]["media"]

    if not anime_list:

        await update.message.reply_text(
            "😔 Koi anime nahi mila.\n\n"
            "Example:\n"
            "Naruto\n"
            "One Piece\n"
            "Demon Slayer"
        )

        context.user_data["search_mode"] = False
        return

    context.user_data["search_mode"] = False

    await update.message.reply_text(
        f"🔎 <b>{len(anime_list)} results mile:</b>",
        parse_mode="HTML"
    )

    for i, anime in enumerate(anime_list, start=1):

        english = anime["title"]["english"]
        romaji = anime["title"]["romaji"]

        title = english or romaji

        year = anime["startDate"]["year"]

        if not year:
            year = "Unknown"

        episodes = anime["episodes"]

        if not episodes:
            episodes = "Unknown"

        score = anime["averageScore"]

        if score:
            rating = f"{score / 10:.1f}/10"
        else:
            rating = "N/A"

        genres = anime["genres"]

        if genres:
            genre_text = ", ".join(genres[:5])
        else:
            genre_text = "N/A"

        status = anime["status"]

        description = anime["description"]

        if not description:
            description = "Description available nahi hai."

        description = description.replace(
            "<br>", " "
        )

        if len(description) > 300:
            description = description[:300] + "..."

        message = (
            f"🎬 <b>{i}. {title}</b>\n\n"
            f"🇯🇵 Romaji: {romaji}\n"
            f"📅 Year: {year}\n"
            f"📺 Episodes: {episodes}\n"
            f"⭐ Rating: {rating}\n"
            f"📌 Status: {status}\n"
            f"🎭 Genres: {genre_text}\n\n"
            f"📝 {description}"
        )

        # =====================
        # LINKS
        # =====================

        links = anime.get("externalLinks", [])

        if links:

            message += "\n\n🔗 <b>Official / External Links:</b>\n"

            for link in links[:5]:

                site = link.get("site")
                url = link.get("url")

                if site and url:

                    message += (
                        f'• <a href="{url}">{site}</a>\n'
                    )

        # AniList page
        if anime.get("siteUrl"):

            message += (
                f'\n📚 <a href="{anime["siteUrl"]}">'
                f'View on AniList</a>'
            )

        # India watch note
        message += (
            "\n\n🇮🇳 <b>Where to Watch — India</b>\n"
            "Streaming availability title aur region "
            "ke according change ho sakti hai."
        )

        poster = anime["coverImage"]["large"]

        if poster:

            await update.message.reply_photo(
                photo=poster,
                caption=message,
                parse_mode="HTML"
            )

        else:

            await update.message.reply_text(
                message,
                parse_mode="HTML"
            )


# =========================
# RANDOM ANIME
# =========================

async def random_anime(update, context):

    await update.message.reply_text(
        "🎯 Random anime choose kar raha hoon..."
    )

    query = """
    query {
        Page(page: 1, perPage: 50) {
            media(
                type: ANIME,
                isAdult: false
            ) {
                id

                title {
                    romaji
                    english
                }

                startDate {
                    year
                }

                episodes

                averageScore

                genres

                coverImage {
                    large
                }

                siteUrl
            }
        }
    }
    """

    data = await anilist_request(query)

    if not data:

        await update.message.reply_text(
            "❌ Database response nahi de raha."
        )
        return

    anime_list = data["data"]["Page"]["media"]

    if not anime_list:
        await update.message.reply_text(
            "😔 Anime nahi mila."
        )
        return

    anime = random.choice(anime_list)

    title = anime["title"]["english"] or anime["title"]["romaji"]

    year = anime["startDate"]["year"] or "Unknown"

    episodes = anime["episodes"] or "Unknown"

    score = anime["averageScore"]

    rating = (
        f"{score / 10:.1f}/10"
        if score
        else "N/A"
    )

    genres = ", ".join(
        anime["genres"][:5]
    )

    message = (
        "🎯 <b>Random Anime</b>\n\n"
        f"🎬 <b>{title}</b>\n"
        f"📅 Year: {year}\n"
        f"📺 Episodes: {episodes}\n"
        f"⭐ Rating: {rating}\n"
        f"🎭 Genres: {genres}\n\n"
        f'📚 <a href="{anime["siteUrl"]}">'
        "View on AniList</a>"
    )

    await update.message.reply_photo(
        photo=anime["coverImage"]["large"],
        caption=message,
        parse_mode="HTML"
    )


# =========================
# TRENDING
# =========================

async def trending_anime(update, context):

    await update.message.reply_text(
        "🔥 Trending anime load ho rahe hain..."
    )

    query = """
    query {

        Page(page: 1, perPage: 10) {

            media(
                type: ANIME,
                isAdult: false,
                sort: TRENDING_DESC
            ) {

                title {
                    romaji
                    english
                }

                startDate {
                    year
                }

                averageScore

                coverImage {
                    large
                }

                siteUrl
            }
        }
    }
    """

    data = await anilist_request(query)

    if not data:

        await update.message.reply_text(
            "❌ Trending data nahi mila."
        )
        return

    anime_list = data["data"]["Page"]["media"]

    for i, anime in enumerate(anime_list, start=1):

        title = anime["title"]["english"] or anime["title"]["romaji"]

        year = anime["startDate"]["year"] or "Unknown"

        score = anime["averageScore"]

        rating = (
            f"{score / 10:.1f}/10"
            if score
            else "N/A"
        )

        message = (
            f"🔥 <b>{i}. {title}</b>\n"
            f"📅 {year}\n"
            f"⭐ {rating}\n\n"
            f'<a href="{anime["siteUrl"]}">'
            "View Details</a>"
        )

        await update.message.reply_photo(
            photo=anime["coverImage"]["large"],
            caption=message,
            parse_mode="HTML"
        )


# =========================
# TOP RATED
# =========================

async def top_rated(update, context):

    await update.message.reply_text(
        "📊 Top rated anime load ho rahe hain..."
    )

    query = """
    query {

        Page(page: 1, perPage: 10) {

            media(
                type: ANIME,
                isAdult: false,
                sort: SCORE_DESC
            ) {

                title {
                    romaji
                    english
                }

                averageScore

                startDate {
                    year
                }

                coverImage {
                    large
                }

                siteUrl
            }
        }
    }
    """

    data = await anilist_request(query)

    if not data:

        await update.message.reply_text(
            "❌ Top rated data nahi mila."
        )
        return

    anime_list = data["data"]["Page"]["media"]

    for i, anime in enumerate(anime_list, start=1):

        title = anime["title"]["english"] or anime["title"]["romaji"]

        score = anime["averageScore"]

        rating = (
            f"{score / 10:.1f}/10"
            if score
            else "N/A"
        )

        message = (
            f"🏆 <b>{i}. {title}</b>\n\n"
            f"⭐ Rating: {rating}\n"
            f"📅 Year: "
            f"{anime['startDate']['year'] or 'Unknown'}\n\n"
            f'<a href="{anime["siteUrl"]}">'
            "View Details</a>"
        )

        await update.message.reply_photo(
            photo=anime["coverImage"]["large"],
            caption=message,
            parse_mode="HTML"
        )


# =========================
# RECENTLY RELEASED
# =========================

async def recently_released(update, context):

    await update.message.reply_text(
        "🆕 Recently released anime load ho rahe hain..."
    )

    query = """
    query {

        Page(page: 1, perPage: 10) {

            media(
                type: ANIME,
                isAdult: false,
                sort: START_DATE_DESC
            ) {

                title {
                    romaji
                    english
                }

                startDate {
                    year
                    month
                    day
                }

                averageScore

                coverImage {
                    large
                }

                siteUrl
            }
        }
    }
    """

    data = await anilist_request(query)

    if not data:

        await update.message.reply_text(
            "❌ Recent anime data nahi mila."
        )
        return

    anime_list = data["data"]["Page"]["media"]

    for i, anime in enumerate(anime_list, start=1):

        title = anime["title"]["english"] or anime["title"]["romaji"]

        date = anime["startDate"]

        if date["year"]:

            release_date = (
                f"{date['day'] or '?'}/"
                f"{date['month'] or '?'}/"
                f"{date['year']}"
            )

        else:
            release_date = "Unknown"

        message = (
            f"🆕 <b>{i}. {title}</b>\n\n"
            f"📅 Release: {release_date}\n"
            f"⭐ Rating: "
            f"{(anime['averageScore'] / 10):.1f}/10"
            if anime["averageScore"]
            else "⭐ Rating: N/A"
        )

        message += (
            f'\n\n<a href="{anime["siteUrl"]}">'
            "View Details</a>"
        )

        await update.message.reply_photo(
            photo=anime["coverImage"]["large"],
            caption=message,
            parse_mode="HTML"
        )


# =========================
# GENRES
# =========================

async def show_genres(update, context):

    keyboard = [

        [
            InlineKeyboardButton(
                "⚔️ Action",
                callback_data="genre_Action"
            ),
            InlineKeyboardButton(
                "😂 Comedy",
                callback_data="genre_Comedy"
            )
        ],

        [
            InlineKeyboardButton(
                "❤️ Romance",
                callback_data="genre_Romance"
            ),
            InlineKeyboardButton(
                "🧙 Fantasy",
                callback_data="genre_Fantasy"
            )
        ],

        [
            InlineKeyboardButton(
                "🌌 Sci-Fi",
                callback_data="genre_Sci-Fi"
            ),
            InlineKeyboardButton(
                "🕵️ Mystery",
                callback_data="genre_Mystery"
            )
        ],

        [
            InlineKeyboardButton(
                "🏫 School",
                callback_data="genre_School"
            ),
            InlineKeyboardButton(
                "🥋 Martial Arts",
                callback_data="genre_Martial-Arts"
            )
        ],

    ]

    await update.message.reply_text(
        "🎭 <b>Select Genre</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# =========================
# GENRE SEARCH
# =========================

async def genre_search(update, context, genre):

    query = """
    query ($genre: String) {

        Page(page: 1, perPage: 10) {

            media(
                genre: $genre,
                type: ANIME,
                isAdult: false,
                sort: POPULARITY_DESC
            ) {

                title {
                    romaji
                    english
                }

                startDate {
                    year
                }

                averageScore

                coverImage {
                    large
                }

                siteUrl
            }
        }
    }
    """

    data = await anilist_request(
        query,
        {
            "genre": genre
        }
    )

    if not data:

        await update.callback_query.message.reply_text(
            "❌ Genre data nahi mila."
        )
        return

    anime_list = data["data"]["Page"]["media"]

    await update.callback_query.message.reply_text(
        f"🎭 <b>{genre} Anime</b>",
        parse_mode="HTML"
    )

    for i, anime in enumerate(anime_list, start=1):

        title = anime["title"]["english"] or anime["title"]["romaji"]

        score = anime["averageScore"]

        rating = (
            f"{score / 10:.1f}/10"
            if score
            else "N/A"
        )

        message = (
            f"🎬 <b>{i}. {title}</b>\n"
            f"📅 Year: "
            f"{anime['startDate']['year'] or 'Unknown'}\n"
            f"⭐ Rating: {rating}\n\n"
            f'<a href="{anime["siteUrl"]}">'
            "View Details</a>"
        )

        await update.callback_query.message.reply_photo(
            photo=anime["coverImage"]["large"],
            caption=message,
            parse_mode="HTML"
        )


# =========================
# BUTTON HANDLER
# =========================

async def button_handler(update, context):

    query = update.callback_query

    await query.answer()

    data = query.data

    if data.startswith("genre_"):

        genre = data.replace(
            "genre_",
            ""
        )

        await genre_search(
            update,
            context,
            genre
        )


# =========================
# TEXT MENU
# =========================

async def menu_handler(update, context):

    text = update.message.text

    if text == "🔎 Search":

        context.user_data["search_mode"] = True

        await update.message.reply_text(
            "🔎 Anime ka naam type karo:\n\n"
            "Example: <b>Naruto</b>",
            parse_mode="HTML"
        )

    elif text == "🎯 Random Anime":

        await random_anime(
            update,
            context
        )

    elif text == "🔥 Trending Anime":

        await trending_anime(
            update,
            context
        )

    elif text == "📊 Top Rated":

        await top_rated(
            update,
            context
        )

    elif text == "🆕 Recently Released":

        await recently_released(
            update,
            context
        )

    elif text == "🎭 Genres":

        await show_genres(
            update,
            context
        )

    elif text == "⭐ Best Anime":

        await top_rated(
            update,
            context
        )

    elif text == "🇨🇳 Best Donghua":

        await update.message.reply_text(
            "🇨🇳 Donghua section next update mein "
            "dedicated database ke saath add karenge."
        )

    elif text == "❤️ Favorites":

        await update.message.reply_text(
            "❤️ Favorites system next update mein add hoga."
        )

    elif text == "📺 Where to Watch":

        await update.message.reply_text(
            "🇮🇳 <b>Where to Watch — India</b>\n\n"
            "Legal platforms ke links sirf "
            "verified availability ke basis par "
            "dikhaye jayenge.\n\n"
            "Available platforms mein title ke "
            "according se Crunchyroll, Netflix, "
            "Prime Video jaise services ho sakti hain.",
            parse_mode="HTML"
        )

    elif text == "💡 Recommendations":

        await update.message.reply_text(
            "💡 Recommendation system next update mein "
            "add karenge."
        )

    elif text == "⚙️ Settings":

        await update.message.reply_text(
            "⚙️ Settings\n\n"
            "Language: Hindi/English\n"
            "Region: 🇮🇳 India"
        )

    else:

        # Agar search mode ON hai
        if context.user_data.get("search_mode"):

            await search_anime(
                update,
                context
            )


# =========================
# RENDER HTTP SERVER
# =========================

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Anime bot is running!")

    def log_message(self, format, *args):
        return


def start_http_server():
    port = int(os.environ.get("PORT", "10000"))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    print(f"HTTP server listening on port {port}")
    server.serve_forever()


# =========================
# MAIN
# =========================

def main():

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            button_handler
        )
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            menu_handler
        )
    )

    print("🤖 Anime & Donghua Finder started...")

    # Render Web Service requires an HTTP port.
    threading.Thread(target=start_http_server, daemon=True).start()

    app.run_polling()


# =========================
# RUN
# =========================

if __name__ == "__main__":
    main()