#!/usr/bin/env python3
"""
PHASE 3: DIXON-COLES MODEL IMPLEMENTATION
Clean version without emojis or UTF-8 issues
Building on existing database schema
"""

import psycopg2
import numpy as np
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
import sys
import math

def setup_database():
    """Setup database connection and ensure features table exists"""
    print("=" * 70)
    print("PHASE 3: DIXON-COLES MODEL SETUP")
    print("=" * 70)
    
    try:
        conn = psycopg2.connect(
            host='localhost',
            port=5433,
            database='football_betting',
            user='betting_user',
            password='betting_password'
        )
        conn.autocommit = False
        cursor = conn.cursor()
        
        print("[1/5] Database connection: SUCCESS")
        
        # Create features schema if not exists
        cursor.execute("CREATE SCHEMA IF NOT EXISTS features;")
        
        # Create match_features table based on existing schema
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS features.match_features (
                fixture_id VARCHAR(255) PRIMARY KEY,
                dc_home_prob DECIMAL(5,4),
                dc_draw_prob DECIMAL(5,4),
                dc_away_prob DECIMAL(5,4),
                dc_attack_home DECIMAL(8,6),
                dc_attack_away DECIMAL(8,6),
                dc_defense_home DECIMAL(8,6),
                dc_defense_away DECIMAL(8,6),
                dc_rho_parameter DECIMAL(8,6),
                dc_xi_parameter DECIMAL(8,6),
                dc_home_advantage DECIMAL(8,6),
                dc_expected_home_goals DECIMAL(8,6),
                dc_expected_away_goals DECIMAL(8,6),
                calculated_at TIMESTAMP DEFAULT NOW()
            );
        """)
        
        conn.commit()
        print("[2/5] Features table setup: SUCCESS")
        
        return conn, cursor
        
    except Exception as e:
        print(f"[ERROR] Database setup failed: {e}")
        sys.exit(1)

def get_training_data(cursor, limit=1000):
    """Get historical match data for training"""
    print("\n[3/5] Fetching training data...")
    
    query = """
        SELECT 
            external_id as fixture_id,
            home_team_name,
            away_team_name,
            home_goals,
            away_goals,
            match_date
        FROM raw.fixtures 
        WHERE home_goals IS NOT NULL 
            AND away_goals IS NOT NULL
        ORDER BY match_date DESC
        LIMIT %s;
    """
    
    cursor.execute(query, (limit,))
    matches = cursor.fetchall()
    
    if len(matches) < 100:
        print(f"ERROR: Only {len(matches)} matches found. Need at least 100.")
        return None
    
    print(f"SUCCESS: Retrieved {len(matches)} historical matches")
    return matches

class DixonColesModel:
    """Dixon-Coles model implementation based on research specifications"""
    
    def __init__(self, xi=0.0065, home_advantage=0.3, rho=-0.13):
        """
        Initialize Dixon-Coles model with research parameters
        
        Args:
            xi: Time decay parameter (0.0065 from research)
            home_advantage: Home advantage factor (0.3 = 30%)
            rho: Dependence parameter for low-scoring matches
        """
        self.xi = xi
        self.home_advantage = home_advantage
        self.rho = rho
        self.team_attack = {}  # Attack strength for each team
        self.team_defense = {}  # Defense strength for each team
        self.teams = set()
        
    def time_decay_weight(self, match_date, current_date):
        """Calculate time decay weight: exp(-xi * days_difference)"""
        days_diff = (current_date - match_date).days
        return math.exp(-self.xi * days_diff)
    
    def tau_correction(self, home_goals, away_goals, lambda_h, mu_a):
        """
        Tau correction function for low-scoring matches
        Based on Dixon-Coles 1997 formula
        """
        if home_goals == 0 and away_goals == 0:
            return 1 - lambda_h * mu_a * self.rho
        elif home_goals == 0 and away_goals == 1:
            return 1 + lambda_h * self.rho
        elif home_goals == 1 and away_goals == 0:
            return 1 + mu_a * self.rho
        elif home_goals == 1 and away_goals == 1:
            return 1 - self.rho
        else:
            return 1.0
    
    def fit(self, matches, current_date=None):
        """
        Fit Dixon-Coles model to historical matches
        
        Args:
            matches: List of match tuples
            current_date: Reference date for time weighting
        """
        print("[4/5] Training Dixon-Coles model...")
        
        if current_date is None:
            # Use most recent match date
            current_date = max(match[5] for match in matches)
        
        # Collect team statistics with time weighting
        team_stats = {}
        
        for match in matches:
            fixture_id, home_team, away_team, home_goals, away_goals, match_date = match
            
            # Add teams to set
            self.teams.add(home_team)
            self.teams.add(away_team)
            
            # Calculate time weight
            weight = self.time_decay_weight(match_date, current_date)
            
            # Initialize team stats if needed
            if home_team not in team_stats:
                team_stats[home_team] = {
                    'goals_scored': 0.0,
                    'goals_conceded': 0.0,
                    'weighted_matches': 0.0
                }
            if away_team not in team_stats:
                team_stats[away_team] = {
                    'goals_scored': 0.0,
                    'goals_conceded': 0.0,
                    'weighted_matches': 0.0
                }
            
            # Update home team stats with time weighting
            team_stats[home_team]['goals_scored'] += home_goals * weight
            team_stats[home_team]['goals_conceded'] += away_goals * weight
            team_stats[home_team]['weighted_matches'] += weight
            
            # Update away team stats with time weighting
            team_stats[away_team]['goals_scored'] += away_goals * weight
            team_stats[away_team]['goals_conceded'] += home_goals * weight
            team_stats[away_team]['weighted_matches'] += weight
        
        # Calculate league average goals (weighted)
        total_weighted_goals = sum(stats['goals_scored'] for stats in team_stats.values())
        total_weighted_matches = sum(stats['weighted_matches'] for stats in team_stats.values())
        league_avg_goals = total_weighted_goals / total_weighted_matches if total_weighted_matches > 0 else 1.5
        
        print(f"  - League average goals: {league_avg_goals:.3f}")
        print(f"  - Teams analyzed: {len(team_stats)}")
        
        # Calculate attack and defense parameters
        for team, stats in team_stats.items():
            if stats['weighted_matches'] > 0:
                avg_scored = stats['goals_scored'] / stats['weighted_matches']
                avg_conceded = stats['goals_conceded'] / stats['weighted_matches']
                
                attack = avg_scored / league_avg_goals
                defense = avg_conceded / league_avg_goals
                
                self.team_attack[team] = attack
                self.team_defense[team] = defense
        
        # Normalize parameters (sum of attack parameters = 1)
        avg_attack = np.mean(list(self.team_attack.values())) if self.team_attack else 1.0
        for team in self.team_attack:
            self.team_attack[team] /= avg_attack
            self.team_defense[team] /= avg_attack
        
        print("  - Model training complete")
        return True
    
    def predict(self, home_team, away_team):
        """
        Predict match outcome probabilities
        
        Returns:
            Dictionary with probabilities and model parameters
        """
        # Get team parameters (default to 1.0 if not trained)
        home_attack = self.team_attack.get(home_team, 1.0)
        home_defense = self.team_defense.get(home_team, 1.0)
        away_attack = self.team_attack.get(away_team, 1.0)
        away_defense = self.team_defense.get(away_team, 1.0)
        
        # Apply home advantage
        home_attack_adj = home_attack * (1 + self.home_advantage)
        
        # Expected goals (Poisson means)
        lambda_h = home_attack_adj * away_defense
        mu_a = away_attack * home_defense
        
        # Calculate probabilities for reasonable scorelines
        max_goals = 6
        home_win_prob = 0.0
        draw_prob = 0.0
        away_win_prob = 0.0
        
        for i in range(max_goals + 1):
            for j in range(max_goals + 1):
                # Poisson probability
                poisson_prob = (math.exp(-lambda_h) * (lambda_h ** i) / math.factorial(i)) * \
                              (math.exp(-mu_a) * (mu_a ** j) / math.factorial(j))
                
                # Apply tau correction
                tau = self.tau_correction(i, j, lambda_h, mu_a)
                score_prob = poisson_prob * tau
                
                if i > j:
                    home_win_prob += score_prob
                elif i == j:
                    draw_prob += score_prob
                else:
                    away_win_prob += score_prob
        
        # Normalize to ensure sum = 1
        total = home_win_prob + draw_prob + away_win_prob
        if total > 0:
            home_win_prob /= total
            draw_prob /= total
            away_win_prob /= total
        
        return {
            'home_win_prob': home_win_prob,
            'draw_prob': draw_prob,
            'away_win_prob': away_win_prob,
            'expected_home_goals': lambda_h,
            'expected_away_goals': mu_a,
            'home_attack': home_attack,
            'home_defense': home_defense,
            'away_attack': away_attack,
            'away_defense': away_defense,
            'rho': self.rho,
            'xi': self.xi
        }
    
    def calculate_brier_score(self, predicted, actual_result):
        """
        Calculate multi-class Brier score
        
        Args:
            predicted: Tuple of (home_prob, draw_prob, away_prob)
            actual_result: 'H', 'D', or 'A'
        
        Returns:
            Brier score (lower is better)
        """
        if actual_result == 'H':
            actual = (1, 0, 0)
        elif actual_result == 'D':
            actual = (0, 1, 0)
        elif actual_result == 'A':
            actual = (0, 0, 1)
        else:
            raise ValueError("Invalid actual_result")
        
        squared_errors = [(p - a) ** 2 for p, a in zip(predicted, actual)]
        return sum(squared_errors) / 3.0

def store_predictions(cursor, predictions):
    """Store predictions to database"""
    print("\n[5/5] Storing predictions to database...")
    
    stored_count = 0
    for pred in predictions:
        try:
            cursor.execute("""
                INSERT INTO features.match_features 
                (fixture_id, dc_home_prob, dc_draw_prob, dc_away_prob,
                 dc_attack_home, dc_attack_away, dc_defense_home, dc_defense_away,
                 dc_rho_parameter, dc_xi_parameter, dc_home_advantage,
                 dc_expected_home_goals, dc_expected_away_goals, calculated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (fixture_id) DO UPDATE SET
                    dc_home_prob = EXCLUDED.dc_home_prob,
                    dc_draw_prob = EXCLUDED.dc_draw_prob,
                    dc_away_prob = EXCLUDED.dc_away_prob,
                    dc_attack_home = EXCLUDED.dc_attack_home,
                    dc_attack_away = EXCLUDED.dc_attack_away,
                    dc_defense_home = EXCLUDED.dc_defense_home,
                    dc_defense_away = EXCLUDED.dc_defense_away,
                    dc_rho_parameter = EXCLUDED.dc_rho_parameter,
                    dc_xi_parameter = EXCLUDED.dc_xi_parameter,
                    dc_home_advantage = EXCLUDED.dc_home_advantage,
                    dc_expected_home_goals = EXCLUDED.dc_expected_home_goals,
                    dc_expected_away_goals = EXCLUDED.dc_expected_away_goals,
                    calculated_at = EXCLUDED.calculated_at
            """, (
                pred['fixture_id'],
                pred['home_win_prob'],
                pred['draw_prob'],
                pred['away_win_prob'],
                pred['home_attack'],
                pred['away_attack'],
                pred['home_defense'],
                pred['away_defense'],
                pred['rho'],
                pred['xi'],
                pred.get('home_advantage', 0.3),
                pred['expected_home_goals'],
                pred['expected_away_goals']
            ))
            stored_count += 1
        except Exception as e:
            print(f"  Warning: Could not store {pred['fixture_id']}: {e}")
    
    return stored_count

def main():
    """Main execution function"""
    # Setup database
    conn, cursor = setup_database()
    
    try:
        # Get training data
        matches = get_training_data(cursor, limit=1000)
        if not matches:
            return
        
        # Split into training and testing sets
        split_idx = int(len(matches) * 0.8)
        train_matches = matches[:split_idx]
        test_matches = matches[split_idx:]
        
        print(f"  - Training set: {len(train_matches)} matches")
        print(f"  - Testing set: {len(test_matches)} matches")
        
        # Train model
        model = DixonColesModel(xi=0.0065, home_advantage=0.3, rho=-0.13)
        model.fit(train_matches)
        
        # Make predictions on test set
        predictions = []
        brier_scores = []
        
        print("\nMaking predictions on test set...")
        for i, match in enumerate(test_matches):
            fixture_id, home_team, away_team, home_goals, away_goals, match_date = match
            
            # Get prediction
            pred = model.predict(home_team, away_team)
            pred['fixture_id'] = fixture_id
            
            # Determine actual result
            if home_goals > away_goals:
                actual_result = 'H'
            elif home_goals < away_goals:
                actual_result = 'A'
            else:
                actual_result = 'D'
            
            # Calculate Brier score
            brier = model.calculate_brier_score(
                (pred['home_win_prob'], pred['draw_prob'], pred['away_win_prob']),
                actual_result
            )
            brier_scores.append(brier)
            
            predictions.append(pred)
            
            # Show first 3 predictions
            if i < 3:
                print(f"\n  Sample prediction {i+1}:")
                print(f"    Match: {home_team} vs {away_team}")
                print(f"    Probabilities: H={pred['home_win_prob']:.3f}, D={pred['draw_prob']:.3f}, A={pred['away_win_prob']:.3f}")
                print(f"    Actual: {actual_result} ({home_goals}-{away_goals})")
                print(f"    Brier Score: {brier:.4f}")
        
        # Calculate statistics
        avg_brier = np.mean(brier_scores) if brier_scores else 0
        min_brier = np.min(brier_scores) if brier_scores else 0
        max_brier = np.max(brier_scores) if brier_scores else 0
        
        print("\n" + "=" * 70)
        print("MODEL PERFORMANCE SUMMARY")
        print("=" * 70)
        print(f"Average Brier Score: {avg_brier:.4f}")
        print(f"Minimum Brier Score: {min_brier:.4f}")
        print(f"Maximum Brier Score: {max_brier:.4f}")
        
        # Benchmark against random guessing
        random_benchmark = 0.222  # Random guess: 0.33 for each outcome
        if avg_brier < random_benchmark:
            print(f"RESULT: Model outperforms random guessing ({random_benchmark:.3f} benchmark)")
        else:
            print(f"RESULT: Model needs improvement (random: {random_benchmark:.3f})")
        
        # Store predictions
        stored_count = store_predictions(cursor, predictions)
        conn.commit()
        
        print(f"\nStored {stored_count} predictions to database")
        
        # Final verification
        cursor.execute("SELECT COUNT(*) FROM features.match_features;")
        total_predictions = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT 
                AVG(dc_home_prob) as avg_home,
                AVG(dc_draw_prob) as avg_draw,
                AVG(dc_away_prob) as avg_away
            FROM features.match_features;
        """)
        avg_probs = cursor.fetchone()
        
        print("\n" + "=" * 70)
        print("PHASE 3 COMPLETION REPORT")
        print("=" * 70)
        print(f"Total predictions in database: {total_predictions}")
        print(f"Average probabilities - Home: {avg_probs[0]:.3f}, Draw: {avg_probs[1]:.3f}, Away: {avg_probs[2]:.3f}")
        print(f"Model trained on: {len(train_matches)} matches")
        print(f"Predictions validated on: {len(test_matches)} matches")
        print(f"Research parameters used:")
        print(f"  - Time decay (xi): 0.0065")
        print(f"  - Home advantage: 30%")
        print(f"  - Dependence parameter (rho): -0.13")
        print("\nPhase 3 Week 1 objectives achieved!")
        print("=" * 70)
        
    finally:
        # Clean up
        cursor.close()
        conn.close()

if __name__ == "__main__":
    main()
