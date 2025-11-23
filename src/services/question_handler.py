from src.agents.detective import DetectiveAgent
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)

async def handle_question(
    user_id: str,
    phone: str,
    text: str,
    classification: dict,
    db: Session
) -> str:
    """
    Process user questions about legislation (DUVIDA classification)

    Flow:
    1. Extract theme and keywords from classification
    2. Use DetectiveAgent to search related PLs
    3. Register view interactions for analytics
    4. Format friendly response with PL summaries

    Args:
        user_id: UUID of the user
        phone: User's phone number
        text: Original user message
        classification: Classification result from Gemini
        db: Database session

    Returns:
        Formatted response text with PLs or suggestion to create demand

    Example:
        Input: "Existe lei sobre impostos de remédios?"
        Output: "📚 Encontrei 2 projeto(s) de lei sobre saúde:
                 1. PL 1234/2024 - Reduz impostos sobre medicamentos..."
    """

    detective = DetectiveAgent()

    theme = classification.get('theme', 'outros')
    keywords = classification.get('keywords', [])

    logger.info(f"❓ Processing question for user {user_id}: theme={theme}, keywords={keywords}")

    try:
        # Search for related PLs
        pls = await detective.find_related_pls(theme, keywords, db)

        if not pls:
            # No PLs found - suggest creating a demand
            response = f"""📚 Busquei projetos de lei sobre **{theme}**, mas não encontrei nada recente relacionado.

💡 Isso pode significar que ainda não existe legislação sobre o tema. Quer criar uma demanda comunitária para pressionar por uma nova lei?

Basta me enviar sua reivindicação que eu ajudo a organizar!"""

            logger.info("📭 No PLs found - suggesting demand creation")
            return response

        # PLs found - register views and format response
        for pl in pls:
            await detective.register_pl_view(user_id, pl['id'], db)

        # Format response with PL summaries
        response = f"📚 Encontrei {len(pls)} projeto(s) de lei sobre **{theme}**:\n\n"

        # Show maximum 3 PLs to avoid overwhelming user
        for i, pl in enumerate(pls[:3], 1):
            response += f"{i}. **{pl['title']}**\n"

            # Add summary if available
            if pl.get('summary'):
                summary_short = pl['summary'][:150]
                if len(pl['summary']) > 150:
                    summary_short += '...'
                response += f"   {summary_short}\n"
            elif pl.get('ementa'):
                ementa_short = pl['ementa'][:150]
                if len(pl['ementa']) > 150:
                    ementa_short += '...'
                response += f"   {ementa_short}\n"

            # Add status
            status = pl.get('status', 'Em tramitação')
            response += f"   📊 Status: {status}\n\n"

        # Add footer message
        response += "💡 **Em breve vou poder explicar esses PLs em linguagem simples!**\n"
        response += "\n🔗 Quer saber mais sobre algum desses projetos? Me pergunte!"

        logger.info(f"✅ Sent {len(pls[:3])} PLs to user")

        return response

    except Exception as e:
        logger.error(f"❌ Error handling question: {e}")
        return """❌ Desculpe, tive um problema ao buscar informações sobre legislação.

Por favor, tente novamente em alguns instantes."""

    finally:
        # Clean up API connections
        await detective.close()
