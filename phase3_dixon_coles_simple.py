#!/usr/bin/env python3
"""
PHASE 3: DIXON-COLES SIMPLIFIED VERSION
Stores only essential columns first
"""

import psycopg2
import numpy as np
from datetime import datetime
import sys
import math

def setup_database():
    """Setup database with simple table"""
    print("=" * 70)
    print("PHASE 3: SIMPLIFIED DIXON-COLES")
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
        
        print("[1/6] Database connection: SUCCESS")
        
        # Create simple table if not exists
        cursor.execute("CREATE SCHEMA IF NOT EXISTS features;")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS features.match_features_simple (
                fixture_id VARCHAR(255) PRIMARY KEY,
                home_team VARCHAR(100),
                away_team VARCHAR(100),
                home_win_prob DECIMAL(5,4),
                draw_prob DECIMAL(5,4),
                away_win_prob DECIMAL(5,4),
                expected_home_goals DECIMAL(8,6),
                expected_away_goals DECIMAL(8,6),
                brier_score DECIMAL(8,6),
                calculated_at TIMESTAMP DEFAULT NOW()
            );
        """)
        
        conn.commit()
        print("[2/6] Simple table created")
        
        return conn, cursor
        
    except Exception as e:
        print(f"[ERROR] Database setup failed: {e}")
        sys.exit(1)

def get_training_data(cursor, limit=1000):
    """Get historical match data"""
    print("\n[3/6] Fetching training data...")
    
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
        print(f"ERROR: Only {len(matches)} matches found")
        return None
    
    print(f"SUCCESS: Retrieved {len(matches)} matches")
    return matches

class SimpleDixonColes:
    """Simplified Dixon-Coles model"""
    
    def __init__(self, xi=0.0065, home_advantage=0.3):
        self.xi = xi
        self.home_advantage = home_advantage
        self.team_attack = {}
        self.team_defense = {}
        
    def fit(self, matches):
        """Simple training based on average goals"""
        print("[4/6] Training model...")
        
        team_stats = {}
        
        for match in matches:
            fixture_id, home_team, away_team, home_goals, away_goals, match_date = match
            
            # Update home team
            if home_team not in team_stats:
                team_stats[home_team] = {'goals_scored': 0, 'goals_conceded': 0, 'matches': 0}
            team_stats[home_team]['goals_scored'] += home_goals
            team_stats[home_team]['goals_conceded'] += away_goals
            team_stats[home_team]['matches'] += 1
            
            # Update away team
            if away_team not in team_stats:
                team_stats[away_team] = {'goals_scored': 0, 'goals_conceded': 0, 'matches': 0}
            team_stats[away_team]['goals_scored'] += away_goals
            team_stats[away_team]['goals_conceded'] += home_goals
            team_stats[away_team]['matches'] += 1
        
        # Calculate league average
        total_goals = sum(stats['goals_scored'] for stats in team_stats.values())
        total_matches = sum(stats['matches'] for stats in team_stats.values())
        league_avg = total_goals / total_matches if total_matches > 0 else 1.5
        
        print(f"  - League average goals: {league_avg:.3f}")
        print(f"  - Teams analyzed: {len(team_stats)}")
        
        # Calculate parameters
        for team, stats in team_stats.items():
            if stats['matches'] > 0:
                attack = (stats['goals_scored'] / stats['matches']) / league_avg
                defense = (stats['goals_conceded'] / stats['matches']) / league_avg
                self.team_attack[team] = attack
                self.team_defense[team] = defense
        
        return True
    
    def predict(self, home_team, away_team):
        """Make prediction"""
        home_attack = self.team_attack.get(home_team, 1.0)
        home_defense = self.team_defense.get(home_team, 1.0)
        away_attack = self.team_attack.get(away_team, 1.0)
        away_defense = self.team_defense.get(away_team, 1.0)
        
        # Apply home advantage
        home_attack_adj = home_attack * (1 + self.home_advantage)
        
        # Expected goals
        home_exp = home_attack_adj * away_defense
        away_exp = away_attack * home_defense
        
        # Calculate probabilities
        max_goals = 5
        home_win = 0.0
        draw = 0.0
        away_win = 0.0
        
        for i in range(max_goals + 1):
            for j in range(max_goals + 1):
                prob = (math.exp(-home_exp) * (home_exp ** i) / math.factorial(i)) * \
                       (math.exp(-away_exp) * (away_exp ** j) / math.factorial(j))
                
                if i > j:
                    home_win += prob
                elif i == j:
                    draw += prob
                else:
                    away_win += prob
        
        # Normalize
        total = home_win + draw + away_win
        if total > 0:
            home_win /= total
            draw /= total
            away_win /= total
        
        return {
            'home_win_prob': home_win,
            'draw_prob': draw,
            'away_win_prob': away_win,
            'expected_home_goals': home_exp,
            'expected_away_goals': away_exp
        }
    
    def calculate_brier(self, predicted, actual_result):
        """Calculate Brier score"""
        if actual_result == 'H':
            actual = (1, 0, 0)
        elif actual_result == 'D':
            actual = (0, 1, 0)
        else:  # 'A'
            actual = (0, 0, 1)
        
        errors = [(p - a) ** 2 for p, a in zip(predicted, actual)]
        return sum(errors) / 3.0

def main():
    """Main execution"""
    # Setup
    conn, cursor = setup_database()
    
    try:
        # Get data
        matches = get_training_data(cursor, limit=1000)
        if not matches:
            return
        
        # Split data
        split_idx = int(len(matches) * 0.8)
        train_matches = matches[:split_idx]
        test_matches = matches[split_idx:]
        
        print(f"  - Training: {len(train_matches)} matches")
        print(f"  - Testing: {len(test_matches)} matches")
        
        # Train model
        model = SimpleDixonColes(xi=0.0065, home_advantage=0.3)
        model.fit(train_matches)
        
        # Make predictions
        print("\n[5/6] Making predictions...")
        predictions = []
        brier_scores = []
        
        for i, match in enumerate(test_matches):
            fixture_id, home_team, away_team, home_goals, away_goals, match_date = match
            
            # Get prediction
            pred = model.predict(home_team, away_team)
            
            # Determine actual result
            if home_goals > away_goals:
                actual_result = 'H'
            elif home_goals < away_goals:
                actual_result = 'A'
            else:
                actual_result = 'D'
            
            # Calculate Brier score
            brier = model.calculate_brier(
                (pred['home_win_prob'], pred['draw_prob'], pred['away_win_prob']),
                actual_result
            )
            brier_scores.append(brier)
            
            # Store for database
            predictions.append({
                'fixture_id': fixture_id,
                'home_team': home_team,
                'away_team': away_team,
                'home_win_prob': pred['home_win_prob'],
                'draw_prob': pred['draw_prob'],
                'away_win_prob': pred['away_win_prob'],
                'expected_home_goals': pred['expected_home_goals'],
                'expected_away_goals': pred['expected_away_goals'],
                'brier_score': brier
            })
            
            # Show samples
            if i < 3:
                print(f"\n  Sample {i+1}:")
                print(f"    {home_team} vs {away_team}")
                print(f"    Prob: H={pred['home_win_prob']:.3f}, D={pred['draw_prob']:.3f}, A={pred['away_win_prob']:.3f}")
                print(f"    Actual: {actual_result} ({home_goals}-{away_goals})")
                print(f"    Brier: {brier:.4f}")
        
        # Statistics
        avg_brier = np.mean(brier_scores)
        print(f"\n  Average Brier Score: {avg_brier:.4f}")
        print(f"  Random baseline: 0.222")
        
        if avg_brier < 0.222:
            print("  RESULT: Model beats random guessing!")
        else:
            print("  RESULT: Model needs improvement")
        
        # Store to database
        print("\n[6/6] Storing predictions...")
        stored_count = 0
        
        for pred in predictions:
            try:
                cursor.execute("""
                    INSERT INTO features.match_features_simple 
                    (fixture_id, home_team, away_team, 
                     home_win_prob, draw_prob, away_win_prob,
                     expected_home_goals, expected_away_goals, brier_score, calculated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (fixture_id) DO UPDATE SET
                        home_team = EXCLUDED.home_team,
                        away_team = EXCLUDED.away_team,
                        home_win_prob = EXCLUDED.home_win_prob,
                        draw_prob = EXCLUDED.draw_prob,
                        away_win_prob = EXCLUDED.away_win_prob,
                        expected_home_goals = EXCLUDED.expected_home_goals,
                        expected_away_goals = EXCLUDED.expected_away_goals,
                        brier_score = EXCLUDED.brier_score,
                        calculated_at = EXCLUDED.calculated_at
                """, (
                    pred['fixture_id'],
                    pred['home_team'],
                    pred['away_team'],
                    pred['home_win_prob'],
                    pred['draw_prob'],
                    pred['away_win_prob'],
                    pred['expected_home_goals'],
                    pred['expected_away_goals'],
                    pred['brier_score']
                ))
                stored_count += 1
            except Exception as e:
                print(f"  Warning: Could not store {pred['fixture_id']}: {e}")
                conn.rollback()
                continue
        
        conn.commit()
        print(f"  Stored {stored_count} predictions")
        
        # Verify
        cursor.execute("SELECT COUNT(*) FROM features.match_features_simple;")
        total = cursor.fetchone()[0]
        
        cursor.execute("SELECT AVG(brier_score) FROM features.match_features_simple;")
        avg_stored_brier = cursor.fetchone()[0]
        
        print("\n" + "=" * 70)
        print("PHASE 3 COMPLETE - SIMPLIFIED VERSION")
        print("=" * 70)
        print(f"Total predictions stored: {total}")
        print(f"Average Brier score in database: {avg_stored_brier:.4f}")
        print(f"Model performance: {'GOOD' if avg_brier < 0.222 else 'NEEDS WORK'}")
        print("\nNext: Run the full version with complete schema")
        print("=" * 70)
        
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    main()
