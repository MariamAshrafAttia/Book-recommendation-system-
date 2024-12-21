import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.sparse import csr_matrix
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.neighbors import NearestNeighbors
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.mixture import GaussianMixture

# Define a class for the book recommendation system
class Recommendation():
    # Initialize the class by loading datasets and preparing the model
    def __init__(self):
        # Load the books, users, and ratings datasets
        self.books = pd.read_csv("DataSet/Books.csv", low_memory=False)
        self.users = pd.read_csv("DataSet/Users.csv")
        self.ratings = pd.read_csv("DataSet/Ratings.csv")

        # Perform data cleaning
        print("Cleaning Data ...")
        self.CleanData()

        # Create the main dataframe combining books, users, and ratings
        print("Creating Dataframe ...")
        self.CreateDataFram()

        # Create the recommendation model
        print("Creating Model ...")
        self.CreateModel()

    # Function to clean the data
    def CleanData(self):
        # Remove duplicate rows and reset the index for the books dataset
        self.books.drop_duplicates(keep="first", inplace=True)
        self.books.reset_index(inplace=True, drop=True)
        # Drop unnecessary columns from the books dataset
        self.books.drop(columns=["Image-URL-S", "Image-URL-M"], inplace=True)
        
        # Remove duplicate rows and reset the index for the users dataset
        self.users.drop_duplicates(keep="first", inplace=True)
        self.users.reset_index(inplace=True, drop=True)

        # Count the number of ratings per user
        self.num_ratings = self.ratings.groupby("User-ID")["Book-Rating"].count()
        # Remove duplicate rows from the ratings dataset
        self.ratings.drop_duplicates(keep="first", inplace=True)
        self.ratings.reset_index(inplace=True, drop=True)

        # Create a new dataframe for user rating counts and merge with the ratings dataset
        self.num_ratings = pd.DataFrame(self.num_ratings)
        self.num_ratings.rename(columns={"Book-Rating": "num_rating"}, inplace=True)
        self.ratings = pd.merge(self.ratings, self.num_ratings, on="User-ID")

        # Filter out users with less than 50 ratings
        self.ratings = self.ratings[self.ratings["num_rating"] > 50]

    # Function to create the main dataframe and prepare the pivot table
    def CreateDataFram(self):
        # Merge ratings and books datasets on ISBN to include book details
        self.df = pd.merge(self.ratings, self.books, on="ISBN")
        # Get the count of ratings for each book and filter books with > 100 ratings
        book_rating_counts = self.df.groupby("Book-Title")["Book-Rating"].count()
        self.df = self.df[self.df["Book-Title"].isin(book_rating_counts[book_rating_counts > 100].index)]

        # Aggregate ratings by user and book to calculate the mean rating
        aggregated_df = self.df.groupby(['User-ID', 'Book-Title']).agg({'Book-Rating': 'mean'}).reset_index()
        # Merge back with the original dataframe to keep book details
        self.df = pd.merge(aggregated_df, self.df.drop(columns=['Book-Rating']), on=['User-ID', 'Book-Title'])
        # Remove duplicate entries
        self.df.drop_duplicates(subset=['User-ID', 'Book-Title'], keep='first', inplace=True)

        # Create a pivot table with books as rows, users as columns, and ratings as values
        self.pivot = self.df.pivot(index='Book-Title', columns='User-ID', values='Book-Rating')
        self.pivot.fillna(value=0, inplace=True)  # Replace NaN with 0
        # Convert the pivot table to a sparse matrix for efficient computations
        self.matrix = csr_matrix(self.pivot)

    # Function to create the recommendation model
    def CreateModel(self):
        # Use the Nearest Neighbors algorithm with cosine similarity
        self.model = NearestNeighbors(n_neighbors=11, algorithm="brute", metric="cosine")
        self.model.fit(self.matrix)

    # Function to get book recommendations based on a given book title
    def GetBookRecommendations(self, book_title):
        # Check if the book title exists in the pivot table
        if book_title not in self.pivot.index:
            return "Book title not found."

        # Find the index of the book in the pivot table
        book_index = self.pivot.index.get_loc(book_title)
        # Find the 10 nearest neighbors (similar books)
        distances, indices = self.model.kneighbors(self.pivot.iloc[book_index, :].values.reshape(1, -1), n_neighbors=11)
        # Get the titles of the recommended books
        recommended_books = [self.pivot.index[i] for i in indices.flatten()][1:]
        
        return recommended_books

    # Function to provide personalized recommendations for a user
    def personalized_book_recommendations(self, user_id):
        # Check if the user ID exists in the pivot table's transpose
        if user_id not in self.transpose_pivot.index:
            return "User ID not found in the dataset."

        # Find similar users based on cosine similarity
        distances, indices = self.model_T.kneighbors(self.transpose_pivot.loc[user_id, :].values.reshape(1, -1), n_neighbors=11)
        similar_users = self.transpose_pivot.index[indices.flatten()][1:]

        # Collect books rated by similar users
        recommended_books = set()
        for user in similar_users:
            top_books = self.df[self.df['User-ID'] == user]['Book-Title'].unique()
            recommended_books.update(top_books)

        # Exclude books already rated by the current user
        user_rated_books = self.df[self.df['User-ID'] == user_id]['Book-Title'].unique()
        final_recommendations = list(recommended_books.difference(user_rated_books))

        return final_recommendations

    # Alternative implementation of personalized recommendations
    def personalized_book_recommendations1(self, user_id):
        # Transpose the pivot table and create a sparse matrix
        self.transpose_pivot = self.pivot.T
        self.matrix_t = csr_matrix(self.transpose_pivot)
        
        # Train a Nearest Neighbors model on the transposed matrix
        self.model_T = NearestNeighbors(algorithm="brute", metric="cosine", n_neighbors=11)
        self.model_T.fit(self.matrix_t)

        # Check if the user ID exists in the transposed pivot table
        if user_id not in self.transpose_pivot.index:
            return "User ID not found in the dataset."

        # Find similar users and recommend books based on their ratings
        distances, indices = self.model_T.kneighbors(self.transpose_pivot.loc[user_id, :].values.reshape(1, -1), n_neighbors=11)
        similar_users = self.transpose_pivot.index[indices.flatten()][1:]
        recommended_books = set()

        for user in similar_users:
            top_books = self.df[self.df['User-ID'] == user]['Book-Title'].unique()
            recommended_books.update(top_books)

        user_rated_books = self.df[self.df['User-ID'] == user_id]['Book-Title'].unique()
        final_recommendations = list(recommended_books.difference(user_rated_books))

        return final_recommendations
