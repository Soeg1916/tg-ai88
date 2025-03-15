from collections import defaultdict
from datetime import datetime, date
import logging

logger = logging.getLogger(__name__)

class MessageCounter:
    def __init__(self):
        # Store counts by date: {date: count}
        self.daily_counts = defaultdict(int)
        # Store total count for the year
        self.yearly_count = 0
        # Store current year
        self.current_year = datetime.now().year

    def add_message(self, timestamp=None):
        """Count a new message."""
        if timestamp is None:
            timestamp = datetime.now()

        message_date = timestamp.date()
        message_year = timestamp.year

        # Only count messages from current year
        if message_year == self.current_year:
            self.daily_counts[message_date] += 1
            self.yearly_count += 1
            logger.info(f"Message counted - Date: {message_date}, Daily count: {self.daily_counts[message_date]}, Yearly total: {self.yearly_count}")

    def get_today_count(self):
        """Get message count for today."""
        today = date.today()
        count = self.daily_counts[today]
        logger.info(f"Retrieved today's count: {count}")
        return count

    def get_year_count(self):
        """Get total message count for the current year."""
        logger.info(f"Retrieved yearly count: {self.yearly_count}")
        return self.yearly_count