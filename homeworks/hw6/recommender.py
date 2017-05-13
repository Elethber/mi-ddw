import csv
from typing import List, Dict, Tuple
from pprint import pprint

import numpy
from sklearn.metrics.pairwise import cosine_similarity

numpy.set_printoptions(precision=2, linewidth=999)

SKIP_GENRES = ['(no genres listed)']
RATING_THRESHOLD = 2.5


class User:
    def __init__(self, user_id, genres_count):
        super().__init__()
        self.id = user_id
        self.genre_ratings = numpy.zeros(genres_count, dtype=int)  # Ratings of genres by the user, normalized to (0,1)
        self.movies_rated = set()

    def __repr__(self, *args, **kwargs):
        return "User[{}]: {}".format(self.id, self.genre_ratings)

    def print_genre_ratings(self, genre_id_to_str, sort_by_name=False):
        print("User {} ratings:".format(self.id))

        if not sort_by_name:
            genre_ratings: List[Tuple[str, float]] = [(genre_id_to_str[i], self.genre_ratings[i]) for i in
                                                      range(0, self.genre_ratings.size)]

            genre_ratings = sorted(genre_ratings, key=lambda rating: rating[1], reverse=True)
            for genre_rating in genre_ratings:
                if genre_rating[1] > 0:
                    print("  {}: {}".format(genre_rating[0], genre_rating[1]))
        else:
            for i in range(0, self.genre_ratings.size):
                if self.genre_ratings[i] > 0:
                    print("  {}: {}".format(genre_id_to_str[i], self.genre_ratings[i]))


class Movie:
    def __init__(self, movie_id, title, genres):
        super().__init__()
        self.id = movie_id
        self.title = title
        self.genres = genres
        self.genres_vector = None

    def populate_genres_vector(self, genres_str_to_int: Dict[str, int]):
        self.genres_vector = numpy.zeros(len(genres_str_to_int))
        for genre in self.genres:
            genre_id = genres_str_to_int[genre]
            self.genres_vector[genre_id] = 1

        self.genres_vector = self.genres_vector.reshape(1, -1)

    def __repr__(self, *args, **kwargs):
        return "{} ({},{})".format(self.title, self.id, self.genres)


class Recommender:
    def __init__(self, movies_csv, ratings_csv):
        super().__init__()

        self.movies_csv_fn = movies_csv
        self.ratings_csv_fn = ratings_csv

        # self.movies: Dict[Movie], self.genres_list: List[str] = self._read_movies()
        self.movies, self.genres_list = self._read_movies()
        self.genre_str_to_id = {genre: i for i, genre in enumerate(self.genres_list)}
        self.genre_id_to_str = {i: genre for i, genre in enumerate(self.genres_list)}
        for movie in self.movies.values():
            movie.populate_genres_vector(self.genre_str_to_id)

        self.users: List[User] = self._read_users()

    def print_user_ratings(self, user_id):
        self.users[user_id].print_genre_ratings(self.genre_id_to_str)

    def recommend_content_based(self, user_id: int, top_n_results: int) -> List[Tuple[int, float]]:
        """
        Recommend top N results with Content-based recommending approach.

        Calculate cosine similarity of the given User's ratings to all movies in the Recommender (similarity
        of rated genres).
        E.g. if user
        :param user_id: ID of the user
        :param top_n_results: Number of top results to return.
        :return: List of (movie_id, similarity) tuples sorted in descending order based on similarity.
        """
        similarities: Dict[int, float] = {}

        non_rated_movies = [movie for movie in self.movies.values() if movie.id not in self.users[user_id].movies_rated]
        for movie in non_rated_movies:
            similarity = cosine_similarity(self.users[user_id].genre_ratings.reshape(1, -1), movie.genres_vector)[0][0]
            similarities[movie.id] = similarity

        # Sort obtained similarities, best first
        sorted_similarities: List[Tuple[int, float]] = sorted(similarities.items(),
                                                              key=lambda item: item[1],
                                                              reverse=True)
        return sorted_similarities[:top_n_results]

    def recommend_collaborative_based(self, user_id: int, top_n_similar_users: int) -> List[Tuple[int, float]]:
        """
        Recommend top N results with Collaborative filtering approach.

        - Calculate cosine similarity of the given user's rating vector to all other users.
        - Select the best N matches
        - Build a new movie rating vector as a weighted mean of all the ratings the other users made.
        - Sort the ratings descendingly, recommend the movies with the highest ranking that the user has not seen yet
        :param user_id:
        :param top_n_similar_users:
        :return:
        """
        this_user = self.users[user_id]

        similarities: Dict[int, float] = {}
        for user in self.users.values():
            if user_id == user.id:
                continue  # skip this user

            similarity = cosine_similarity(this_user.genre_ratings.reshape(1, -1), user.genre_ratings.reshape(1, -1))[0][0]
            similarities[user.id] = similarity

        # Sort obtained similarities, best first
        sorted_similar_users: List[Tuple[int, float]] = sorted(similarities.items(),
                                                               key=lambda item: item[1],
                                                               reverse=True)[:top_n_similar_users]

        # Build a new movie rating from similar users


    def _read_movies(self) -> Tuple[Dict[int, Movie], List[str]]:
        """
        Read datafile with movies.
        :return: Tuple: (
                         dict of Movie objects (key = movie_id),
                         list of genres (as strings)
                        )
        """

        genres_set = set()
        movies = {}

        with open(self.movies_csv_fn, encoding="utf-8") as f:
            f.readline()
            f.readline()
            reader = csv.reader(f, delimiter=',')
            for movie_row in reader:
                # print("Row: {}".format(movie_row))
                movie_id = int(movie_row[0])
                title = movie_row[1]
                genres = [genre.strip() for genre in movie_row[2].split('|') if genre.strip() not in SKIP_GENRES]
                movie = Movie(movie_id, title, genres)
                movies[movie_id] = movie
                genres_set = genres_set.union(set(genres))

        return movies, sorted(list(genres_set))

    def _read_users(self):
        users: Dict[User] = {}

        with open(self.ratings_csv_fn, encoding="utf-8") as f:
            f.readline()
            f.readline()
            reader = csv.reader(f, delimiter=',', )
            for i, rating_row in enumerate(reader):
                user_id = int(rating_row[0])
                movie_id = int(rating_row[1])
                rating = float(rating_row[2])
                if user_id not in users:
                    users[user_id] = User(user_id, len(self.genre_str_to_id))

                users[user_id].movies_rated.add(movie_id)
                for movie_genre in self.movies[movie_id].genres:
                    if rating >= RATING_THRESHOLD:
                        users[user_id].genre_ratings[self.genre_str_to_id[movie_genre]] += 1

        # TODO Not sure about this - normalizing user rating vector to have scores in (0,1).
        # Reason - Vector (3,1,0) would be closer to (0,1,0) than (3,0,0), but user clearly more prefers the first genre
        for user in users.values():
            user.genre_ratings = user.genre_ratings / numpy.amax(user.genre_ratings)

        return users


def main():
    recommender = Recommender('data/movies.csv', 'data/ratings.csv')
    user_id = 1

    # recommended_movies = recommender.recommend_content_based(user_id, 5)
    # pprint(recommended_movies)

    similar_users = recommender.recommend_collaborative_based(user_id, 59999999)
    pprint(similar_users)

    recommender.print_user_ratings(user_id)
    # for id, _ in similar_users[:3]:
    #     recommender.print_user_ratings(id)


if __name__ == '__main__':
    main()
