# PHASE 3 WEEK 2: FEATURE CALCULATOR ENGINE

## í³… Week 2 Objectives
1. **Implement 38+ AlphaBetting features** from research documents
2. **Create feature pipeline** calculating rest differential, form metrics, etc.
3. **Integrate with Dixon-Coles probabilities**
4. **Build feature validation suite**

## í´§ Existing Resources
1. **`feature_engineering.py`** - Provided feature engineering functions
2. **`features.match_features` table** - Contains Dixon-Coles predictions (201 rows)
3. **`raw.fixtures` table** - 40,007 historical matches with goals
4. **Phase 3 Week 1 foundation** - Working Dixon-Coles model

## í³ Expected Week 2 File Structure
alpha_betting_system/
â”œâ”€â”€ src/features/
â”‚ â”œâ”€â”€ feature_calculator.py # Main feature calculator engine
â”‚ â”œâ”€â”€ feature_pipeline.py # Feature calculation pipeline
â”‚ â”œâ”€â”€ feature_validation.py # Feature validation and testing
â”‚ â””â”€â”€ dixon_coles.py # Existing model (enhance with features)
â”œâ”€â”€ run_feature_pipeline.py # Runner script for feature calculation
â”œâ”€â”€ test_features.py # Feature validation tests
â””â”€â”€ PHASE3_WEEK2_REPORT.md # Week 2 progress report

## í¾¯ Key Features to Implement (from research)
Based on provided `feature_engineering.py` and research documents:

### **Form Features:**
- Recent form (last 3, 5, 10 matches)
- Win/loss/draw streaks
- Home/away form differential

### **Goal-Based Features:**
- Expected goals (xG) metrics
- Goal difference in recent matches
- Clean sheet probability

### **Team Strength Features:**
- Elo ratings (offensive/defensive)
- Attack/defense parameters from Dixon-Coles
- Home advantage metrics

### **Contextual Features:**
- Rest differential (days since last match)
- Matchday importance (end of season)
- Head-to-head history

### **Market Features:**
- Odds movements
- Market probabilities
- Value bet identification

## íº€ Week 2 Implementation Plan

### **Day 1-2: Feature Calculator Engine**
1. Create `feature_calculator.py` with core feature calculations
2. Integrate existing `feature_engineering.py` functions
3. Add database integration for feature storage

### **Day 3-4: Feature Pipeline**
1. Create `feature_pipeline.py` for batch feature calculation
2. Add incremental update capability
3. Implement feature validation and quality checks

### **Day 5-7: Integration & Testing**
1. Integrate features with Dixon-Coles predictions
2. Create feature validation suite
3. Performance benchmarking
4. Prepare for XGBoost integration (Week 3)

## í³Š Success Criteria
- [ ] 38+ features implemented and validated
- [ ] Features stored in database alongside Dixon-Coles predictions
- [ ] Feature pipeline runs without errors
- [ ] Feature quality metrics documented
- [ ] Ready for XGBoost model training (Week 3)

## í´— Starting Points
1. **Database**: Features should be stored in `features.match_features` table (extend if needed)
2. **Existing Code**: Use `feature_engineering.py` as foundation
3. **Model Integration**: Combine features with Dixon-Coles probabilities
4. **Validation**: Compare feature distributions with research expectations

## â° Timeline
- **Start Date**: Immediate (Phase 3 Week 1 complete)
- **Duration**: 7 days
- **Deliverables**: Feature calculator engine, pipeline, validation suite
- **Dependencies**: Phase 3 Week 1 database and model

---
*Prepared by Technical Assistant*
*Phase 3 Week 2 Starter Plan*
*Date: $(date +"%Y-%m-%d")*
