#!/usr/bin/env python3
"""
AI-Powered Artwork Recommendation Engine for VAPOR
Uses machine learning to select the best artwork based on user preferences
"""

import numpy as np
import tensorflow as tf
from tensorflow import keras
from PIL import Image
import io
import asyncio
from typing import List, Dict, Optional, Tuple
import aiohttp
from sklearn.metrics.pairwise import cosine_similarity
import pickle
import json
from pathlib import Path

class AIRecommendationEngine:
    """
    Advanced AI system for artwork recommendation using:
    - Neural networks for style classification
    - Computer vision for quality assessment
    - Collaborative filtering for user preferences
    - Content-based filtering for game similarity
    """
    
    def __init__(self):
        self.style_model = None
        self.quality_model = None
        self.user_embeddings = {}
        self.game_embeddings = {}
        self.models_loaded = False
        
        # Style categories
        self.style_categories = [
            'minimalist', 'realistic', 'artistic', 'retro', 
            'modern', 'dark', 'colorful', 'abstract'
        ]
        
        # Cache for processed images
        self.image_cache = {}
        
    async def load_models(self):
        """Load pre-trained models asynchronously"""
        try:
            # Load or create models
            model_path = Path("models")
            model_path.mkdir(exist_ok=True)
            
            # Style classification model
            if (model_path / "style_model.h5").exists():
                self.style_model = keras.models.load_model(str(model_path / "style_model.h5"))
            else:
                self.style_model = self._create_style_model()
                
            # Quality assessment model
            if (model_path / "quality_model.h5").exists():
                self.quality_model = keras.models.load_model(str(model_path / "quality_model.h5"))
            else:
                self.quality_model = self._create_quality_model()
                
            # Load user preference embeddings
            if (model_path / "user_embeddings.pkl").exists():
                with open(model_path / "user_embeddings.pkl", "rb") as f:
                    self.user_embeddings = pickle.load(f)
                    
            self.models_loaded = True
            print("✅ AI models loaded successfully")
            
        except Exception as e:
            print(f"❌ Error loading AI models: {e}")
            self.models_loaded = False
    
    def _create_style_model(self) -> keras.Model:
        """Create a CNN for artwork style classification"""
        model = keras.Sequential([
            keras.layers.Conv2D(32, (3, 3), activation='relu', input_shape=(224, 224, 3)),
            keras.layers.MaxPooling2D((2, 2)),
            keras.layers.Conv2D(64, (3, 3), activation='relu'),
            keras.layers.MaxPooling2D((2, 2)),
            keras.layers.Conv2D(128, (3, 3), activation='relu'),
            keras.layers.MaxPooling2D((2, 2)),
            keras.layers.Flatten(),
            keras.layers.Dense(512, activation='relu'),
            keras.layers.Dropout(0.5),
            keras.layers.Dense(len(self.style_categories), activation='softmax')
        ])
        
        model.compile(
            optimizer='adam',
            loss='categorical_crossentropy',
            metrics=['accuracy']
        )
        
        return model
    
    def _create_quality_model(self) -> keras.Model:
        """Create a model for image quality assessment"""
        model = keras.Sequential([
            keras.layers.Conv2D(16, (3, 3), activation='relu', input_shape=(224, 224, 3)),
            keras.layers.MaxPooling2D((2, 2)),
            keras.layers.Conv2D(32, (3, 3), activation='relu'),
            keras.layers.MaxPooling2D((2, 2)),
            keras.layers.Conv2D(64, (3, 3), activation='relu'),
            keras.layers.GlobalAveragePooling2D(),
            keras.layers.Dense(128, activation='relu'),
            keras.layers.Dense(1, activation='sigmoid')  # Quality score 0-1
        ])
        
        model.compile(
            optimizer='adam',
            loss='binary_crossentropy',
            metrics=['mae']
        )
        
        return model
    
    async def recommend_artwork(
        self,
        user_id: str,
        game_id: int,
        available_artwork: List[Dict],
        user_history: Optional[List[Dict]] = None
    ) -> List[Dict]:
        """
        Recommend best artwork for a game based on AI analysis
        
        Returns artwork sorted by recommendation score
        """
        if not self.models_loaded:
            await self.load_models()
            
        recommendations = []
        
        # Analyze each artwork option
        for artwork in available_artwork:
            score = await self._calculate_recommendation_score(
                user_id,
                game_id,
                artwork,
                user_history
            )
            
            artwork['ai_score'] = score
            artwork['ai_reasoning'] = self._generate_reasoning(score)
            recommendations.append(artwork)
        
        # Sort by AI score
        recommendations.sort(key=lambda x: x['ai_score'], reverse=True)
        
        return recommendations
    
    async def _calculate_recommendation_score(
        self,
        user_id: str,
        game_id: int,
        artwork: Dict,
        user_history: Optional[List[Dict]]
    ) -> float:
        """Calculate comprehensive recommendation score"""
        scores = []
        weights = []
        
        # 1. Style matching score (40% weight)
        style_score = await self._get_style_match_score(user_id, artwork)
        scores.append(style_score)
        weights.append(0.4)
        
        # 2. Quality assessment score (30% weight)
        quality_score = await self._assess_image_quality(artwork)
        scores.append(quality_score)
        weights.append(0.3)
        
        # 3. User preference score (20% weight)
        pref_score = self._get_user_preference_score(user_id, artwork)
        scores.append(pref_score)
        weights.append(0.2)
        
        # 4. Community rating score (10% weight)
        community_score = artwork.get('score', 0.5)  # Default to 0.5 if no score
        scores.append(community_score)
        weights.append(0.1)
        
        # Calculate weighted average
        final_score = np.average(scores, weights=weights)
        
        return float(final_score)
    
    async def _get_style_match_score(self, user_id: str, artwork: Dict) -> float:
        """Calculate how well artwork style matches user preferences"""
        if not self.style_model:
            return 0.5
            
        try:
            # Download and process image
            image = await self._download_image(artwork['url'])
            if not image:
                return 0.5
                
            # Prepare image for model
            img_array = self._preprocess_image(image)
            
            # Get style prediction
            style_probs = self.style_model.predict(img_array, verbose=0)[0]
            
            # Get user's preferred styles
            user_pref = self._get_user_style_preference(user_id)
            
            # Calculate similarity
            similarity = cosine_similarity([style_probs], [user_pref])[0][0]
            
            return float(similarity)
            
        except Exception as e:
            print(f"Error in style matching: {e}")
            return 0.5
    
    async def _assess_image_quality(self, artwork: Dict) -> float:
        """Assess technical quality of the image"""
        if not self.quality_model:
            return 0.5
            
        try:
            # Check cache first
            if artwork['id'] in self.image_cache:
                return self.image_cache[artwork['id']]['quality']
                
            # Download image
            image = await self._download_image(artwork['url'])
            if not image:
                return 0.5
                
            # Prepare for model
            img_array = self._preprocess_image(image)
            
            # Get quality prediction
            quality_score = float(self.quality_model.predict(img_array, verbose=0)[0][0])
            
            # Additional quality factors
            resolution_score = self._calculate_resolution_score(image)
            compression_score = self._estimate_compression_quality(artwork)
            
            # Combine scores
            final_quality = (quality_score * 0.6 + 
                           resolution_score * 0.3 + 
                           compression_score * 0.1)
            
            # Cache result
            if artwork['id'] not in self.image_cache:
                self.image_cache[artwork['id']] = {}
            self.image_cache[artwork['id']]['quality'] = final_quality
            
            return final_quality
            
        except Exception as e:
            print(f"Error in quality assessment: {e}")
            return 0.5
    
    def _get_user_preference_score(self, user_id: str, artwork: Dict) -> float:
        """Calculate score based on user's historical preferences"""
        if user_id not in self.user_embeddings:
            return 0.5
            
        # Get user embedding
        user_embed = self.user_embeddings[user_id]
        
        # Create artwork embedding from metadata
        artwork_embed = self._create_artwork_embedding(artwork)
        
        # Calculate similarity
        similarity = cosine_similarity([user_embed], [artwork_embed])[0][0]
        
        return float(similarity)
    
    def _get_user_style_preference(self, user_id: str) -> np.ndarray:
        """Get user's style preference vector"""
        if user_id in self.user_embeddings:
            return self.user_embeddings[user_id].get('style_pref', np.ones(len(self.style_categories)) / len(self.style_categories))
        
        # Return uniform distribution for new users
        return np.ones(len(self.style_categories)) / len(self.style_categories)
    
    async def _download_image(self, url: str) -> Optional[Image.Image]:
        """Download image from URL"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        image_data = await response.read()
                        return Image.open(io.BytesIO(image_data))
        except Exception as e:
            print(f"Error downloading image: {e}")
        
        return None
    
    def _preprocess_image(self, image: Image.Image) -> np.ndarray:
        """Preprocess image for model input"""
        # Resize to model input size
        image = image.resize((224, 224), Image.Resampling.LANCZOS)
        
        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Convert to array and normalize
        img_array = np.array(image) / 255.0
        
        # Add batch dimension
        return np.expand_dims(img_array, axis=0)
    
    def _calculate_resolution_score(self, image: Image.Image) -> float:
        """Calculate score based on image resolution"""
        width, height = image.size
        
        # Ideal resolutions for different artwork types
        ideal_resolutions = {
            'grid': (600, 900),
            'hero': (1920, 620),
            'logo': (256, 256),
            'icon': (512, 512)
        }
        
        # Find closest ideal resolution
        min_diff = float('inf')
        for ideal_w, ideal_h in ideal_resolutions.values():
            diff = abs(width - ideal_w) + abs(height - ideal_h)
            min_diff = min(min_diff, diff)
        
        # Convert to score (0-1)
        score = max(0, 1 - (min_diff / 2000))
        
        return score
    
    def _estimate_compression_quality(self, artwork: Dict) -> float:
        """Estimate compression quality from metadata"""
        # Use file size and dimensions to estimate quality
        file_size = artwork.get('file_size', 0)
        
        if file_size == 0:
            return 0.5
        
        # Rough quality estimation
        if file_size > 2000000:  # > 2MB
            return 0.9
        elif file_size > 1000000:  # > 1MB
            return 0.7
        elif file_size > 500000:  # > 500KB
            return 0.5
        else:
            return 0.3
    
    def _create_artwork_embedding(self, artwork: Dict) -> np.ndarray:
        """Create embedding vector for artwork"""
        # Simple embedding based on metadata
        embedding = []
        
        # Add normalized scores
        embedding.append(artwork.get('score', 0.5))
        embedding.append(artwork.get('nsfw', 0))
        embedding.append(artwork.get('humor', 0))
        embedding.append(artwork.get('epilepsy', 0))
        
        # Add style indicators (simplified)
        style = artwork.get('style', 'default')
        for cat in self.style_categories:
            embedding.append(1.0 if cat in style.lower() else 0.0)
        
        return np.array(embedding)
    
    def _generate_reasoning(self, score: float) -> str:
        """Generate human-readable reasoning for the score"""
        if score >= 0.9:
            return "Perfect match for your preferences"
        elif score >= 0.8:
            return "Excellent match based on your history"
        elif score >= 0.7:
            return "Good match with high quality"
        elif score >= 0.6:
            return "Decent match, above average quality"
        elif score >= 0.5:
            return "Average match, consider alternatives"
        else:
            return "Below average match for your style"
    
    async def update_user_preferences(
        self,
        user_id: str,
        selected_artwork: Dict,
        game_id: int
    ):
        """Update user preferences based on their selection"""
        if user_id not in self.user_embeddings:
            self.user_embeddings[user_id] = {
                'style_pref': np.ones(len(self.style_categories)) / len(self.style_categories),
                'selection_history': []
            }
        
        # Add to selection history
        self.user_embeddings[user_id]['selection_history'].append({
            'game_id': game_id,
            'artwork_id': selected_artwork['id'],
            'timestamp': datetime.utcnow().isoformat()
        })
        
        # Update style preferences using exponential moving average
        if self.style_model and 'url' in selected_artwork:
            image = await self._download_image(selected_artwork['url'])
            if image:
                img_array = self._preprocess_image(image)
                style_probs = self.style_model.predict(img_array, verbose=0)[0]
                
                # Update with EMA (alpha = 0.1)
                alpha = 0.1
                current_pref = self.user_embeddings[user_id]['style_pref']
                self.user_embeddings[user_id]['style_pref'] = (
                    (1 - alpha) * current_pref + alpha * style_probs
                )
        
        # Save updated embeddings
        await self._save_embeddings()
    
    async def _save_embeddings(self):
        """Save user embeddings to disk"""
        model_path = Path("models")
        model_path.mkdir(exist_ok=True)
        
        with open(model_path / "user_embeddings.pkl", "wb") as f:
            pickle.dump(self.user_embeddings, f)
    
    def is_ready(self) -> bool:
        """Check if AI engine is ready"""
        return self.models_loaded