
from datetime import datetime, timezone
from typing import Tuple
import tweepy
import time
from typing import List, Optional
import pandas as pd
import numpy as np
import re


class XClient:
    def __init__(self, bearer_token: Optional[str]):
        self.client = tweepy.Client(bearer_token=bearer_token, wait_on_rate_limit=True)

    def search_recent(
        self,
        query: str,
        max_results: int = 50,
        since_id: Optional[str] = None,
        expansions: List[str] = ["author_id"],
        tweet_fields: List[str] = ["created_at", "lang", "public_metrics"],
        user_fields: List[str] = ["name", "username", "public_metrics"],
    ) -> pd.DataFrame:
        """
        Search recent public tweets (last 7 days on standard tiers).
        Returns a pandas DataFrame.
        """
        # X API returns at most 100 per call
        max_results = min(max_results, 100)

        resp = self.client.search_recent_tweets(
            query=query,
            max_results=max_results,
            since_id=since_id,
            expansions=expansions,
            tweet_fields=tweet_fields,
            user_fields=user_fields,
        )

        if not resp.data:
            return pd.DataFrame(columns=["id", "text", "created_at", "lang", "author_id"])

        # map users
        users = {}
        if resp.includes and "users" in resp.includes:
            for u in resp.includes["users"]:
                users[u.id] = {
                    "author_name": u.name,
                    "author_username": u.username,
                    "author_followers": u.public_metrics.get("followers_count") if u.public_metrics else None,
                }

        rows = []
        for t in resp.data:
            meta = users.get(t.author_id, {}) if hasattr(t, "author_id") else {}
            pm = t.public_metrics if hasattr(t, "public_metrics") and t.public_metrics else {}
            rows.append({
                "id": t.id,
                "text": t.text,
                "created_at": getattr(t, "created_at", None),
                "lang": getattr(t, "lang", None),
                "author_id": getattr(t, "author_id", None),
                "author_name": meta.get("author_name"),
                "author_username": meta.get("author_username"),
                "author_followers": meta.get("author_followers"),
                "retweet_count": pm.get("retweet_count"),
                "reply_count": pm.get("reply_count"),
                "like_count": pm.get("like_count"),
                "quote_count": pm.get("quote_count"),
            })
        return pd.DataFrame(rows)

    def user_by_username(self, username: str):
        return self.client.get_user(username=username)

    def user_tweets(
        self,
        username: str,
        max_results: int = 5,
        tweet_fields: List[str] = ["created_at", "lang", "public_metrics"]
    ) -> pd.DataFrame:
        """
        Get recent tweets from a specific user.
        """
        u = self.user_by_username(username)
        if not u.data:
            return pd.DataFrame(columns=["id", "text", "created_at"])
        uid = u.data.id
        resp = self.client.get_users_tweets(id=uid, max_results=min(max_results, 100), tweet_fields=tweet_fields)
        if not resp.data:
            return pd.DataFrame(columns=["id", "text", "created_at"])

        rows = []
        for t in resp.data:
            pm = t.public_metrics if t.public_metrics else {}
            rows.append({
                "id": t.id,
                "text": t.text,
                "created_at": getattr(t, "created_at", None),
                "lang": getattr(t, "lang", None),
                "retweet_count": pm.get("retweet_count"),
                "reply_count": pm.get("reply_count"),
                "like_count": pm.get("like_count"),
                "quote_count": pm.get("quote_count"),
            })
        return pd.DataFrame(rows)
    
    def users_tweets_bulk(
        self,
        usernames: List[str],
        per_user: int = 5,
        tweet_fields: List[str] = ["created_at", "lang", "public_metrics"],
    ) -> pd.DataFrame:
        """
        Fetch recent tweets for a list of usernames (last 7 days, tier-dependent).
        Returns a single DataFrame with tweets from all provided users.

        - usernames: list of screen names (without @), e.g. ["elonmusk", "CNBC"]
        - per_user: max tweets per user (API limit is 100 per request)
        - tweet_fields: extra fields to fetch for each tweet
        """
        usernames = self._normalize_usernames_input(usernames)
        if not usernames:
            return pd.DataFrame(columns=[
                "id","text","created_at","lang","retweet_count",
                "reply_count","like_count","quote_count","author_id","author_username"
            ])

        # 1) Resolve usernames -> user objects (bulk call)
        resp = self.client.get_users(usernames=list(dict.fromkeys(usernames)))  # dedupe while preserving order
        if not resp.data:
            # no valid users found
            return pd.DataFrame(columns=[
                "id","text","created_at","lang","retweet_count",
                "reply_count","like_count","quote_count","author_id","author_username"
            ])

        id_to_username = {u.id: u.username for u in resp.data}
        user_ids = list(id_to_username.keys())

        # 2) For each user id, fetch their recent tweets
        rows = []
        for uid in user_ids:
            try:
                t_resp = self.client.get_users_tweets(
                    id=uid,
                    max_results=min(per_user, 100),
                    tweet_fields=tweet_fields
                )
            except Exception as e:
                # If one user fails, skip but continue others
                continue

            if not t_resp or not t_resp.data:
                continue

            uname = id_to_username.get(uid)
            for t in t_resp.data:
                pm = t.public_metrics if getattr(t, "public_metrics", None) else {}
                rows.append({
                    "id": t.id,
                    "text": t.text,
                    "created_at": getattr(t, "created_at", None),
                    "lang": getattr(t, "lang", None),
                    "retweet_count": pm.get("retweet_count"),
                    "reply_count": pm.get("reply_count"),
                    "like_count": pm.get("like_count"),
                    "quote_count": pm.get("quote_count"),
                    "author_id": uid,
                    "author_username": uname,
                })

        df = pd.DataFrame(rows)
        if not df.empty:
            # Sort newest first
            if "created_at" in df.columns:
                df = df.sort_values("created_at", ascending=False).reset_index(drop=True)
        return df

    def _normalize_usernames_input(self, usernames) -> list[str]:
        """
        Accepts list/tuple/set/np.ndarray/pd.Series/str and returns a clean list[str]
        without leading '@', deduped and non-empty.
        """
        if isinstance(usernames, pd.DataFrame):
            raise ValueError("Provide a list/Series/array of usernames, not a DataFrame.")
        if isinstance(usernames, (list, tuple, set, np.ndarray, pd.Series)):
            arr = list(usernames)
        elif isinstance(usernames, str):
            arr = [usernames]
        else:
            arr = list(usernames)  # last resort; will error if unsupported

        s = pd.Series(arr, dtype="object").dropna().astype(str).str.strip()
        s = s.str.replace(r'^@', '', regex=True)       # remove leading @
        s = s[s.ne('')]                                # remove empty strings
        return s.drop_duplicates().tolist()

    def _to_rfc3339(self, dt: datetime) -> str:
        """
        Convert a datetime to RFC3339 (UTC, seconds precision) as required by X API.
        Naive datetimes are assumed to be UTC.
        """
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

    def users_tweets_bulk_since(
        self,
        usernames: List[str],
        start_time: datetime,
        end_time: Optional[datetime] = None,
        max_total_per_user: int = 1,#need to change 
        tweet_fields: List[str] = ["created_at", "lang", "public_metrics"],
    ) -> pd.DataFrame:
        """
        Fetch recent tweets for a list of usernames between start_time and end_time (inclusive bounds),
        using pagination per user. Returns a single DataFrame of all tweets.

        Notes:
        - Standard tiers generally limit historical access (often last 7 days).
        - max_total_per_user caps total fetched per user (pagination stops when reached).
        - Requires bearer token with access to the v2 endpoints.
        """
        usernames = self._normalize_usernames_input(usernames)
        if not usernames:
            return pd.DataFrame(columns=[
                "id","text","created_at","lang","retweet_count","reply_count",
                "like_count","quote_count","author_id","author_username"
            ])

        st = self._to_rfc3339(start_time)
        et = self._to_rfc3339(end_time or datetime.now(timezone.utc))

        # Resolve usernames -> user ids (bulk)
        resp = self.client.get_users(usernames=list(dict.fromkeys(usernames)))
        if not resp or not resp.data:
            return pd.DataFrame(columns=[
                "id","text","created_at","lang","retweet_count","reply_count",
                "like_count","quote_count","author_id","author_username"
            ])

        id_to_username = {u.id: u.username for u in resp.data}
        user_ids = list(id_to_username.keys())

        rows = []
        for uid in user_ids:
            fetched = 0
            pagination_token = None

            while fetched < max_total_per_user:
                try:
                    call_max = min(100, max_total_per_user - fetched)
                    r = self.client.get_users_tweets(
                        id=uid,
                        max_results=call_max,
                        tweet_fields=tweet_fields,
                        start_time=st,
                        end_time=et,
                        pagination_token=pagination_token
                    )
                except Exception:
                    # Skip this user on error, continue others
                    break

                if not r or not r.data:
                    break

                uname = id_to_username.get(uid)
                for t in r.data:
                    pm = getattr(t, "public_metrics", None) or {}
                    rows.append({
                        "id": t.id,
                        "text": t.text,
                        "created_at": getattr(t, "created_at", None),
                        "lang": getattr(t, "lang", None),
                        "retweet_count": pm.get("retweet_count"),
                        "reply_count": pm.get("reply_count"),
                        "like_count": pm.get("like_count"),
                        "quote_count": pm.get("quote_count"),
                        "author_id": uid,
                        "author_username": uname,
                    })

                fetched += len(r.data)
                meta = getattr(r, "meta", {}) or {}
                pagination_token = meta.get("next_token")
                if not pagination_token:
                    break

        df = pd.DataFrame(rows)
        if not df.empty and "created_at" in df.columns:
            df["created_at"] = pd.to_datetime(df["created_at"])
            df = df.sort_values("created_at", ascending=False).reset_index(drop=True)
        return df