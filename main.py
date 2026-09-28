"""
Option A, Smart Fitness Session Analyzer
"""

import statistics 

from data_generator import generate_fitness_data

# First class for the fitness tracker and its observations
class Observation:
    def __init__(self, timestamp, heart_rate, skin_response, temperature, activity_level, signal_quality):
        self.timestamp = timestamp
        self.heart_rate = heart_rate
        self.skin_response = skin_response
        self.temperature = temperature
        self.activity_level = activity_level
        self.signal_quality = signal_quality
        
    @classmethod
    def from_dict(cls, data):
        # Will get the information from the dictinary which is produced by the generator provided to us
        return cls(
            timestamp=data["timestamp"],
            heart_rate=data["heart_rate"],
            skin_response=data["skin_response"],
            temperature=data["temperature"],
            activity_level=data["activity_level"],
            signal_quality=data["signal_quality"]
        )
    
    # Check if the observation is valid based on its attributes, usin static methos
    @staticmethod
    def is_within_range(value, lower, upper):
        # THis is a static method since it does not depend on the instance itself, 
        # a simple check for value within a range
        if value is None:
            return False
        return lower <= value <= upper
    
    def is_valid(self):
         """Return (True, "") if this observation is usable, else (False, reason)."""
         if self.heart_rate is None or self.skin_response is None:
            return False, "missing value"
         if not self.is_within_range(self.heart_rate, 30, 220):
            return False, "heart rate out of realistic range"
         if not self.is_within_range(self.activity_level, 0, 1):
            return False, "activity level out of range"
         if not self.is_within_range(self.signal_quality, 0, 1):
            return False, "signal quality out of range"
         if self.signal_quality < 0.6:
            return False, "signal quality too low"
         return True, ""

# Second class as requiremnt from the assignment description
class Participant:
    # THis class wil feature a participant and their personal baselin measurements
    def __init__(self, participant_id, baseline_heart_rate, baseline_skin_response, baseline_temperature):
        self.participant_id = participant_id
        
        # Initialize the protected reference dictionary with baseline values
        self._reference = {
            "heart_rate": baseline_heart_rate,
            
            # This will be the protected attribute which are onlly accessible through the reference dictionary
            "skin_response": baseline_skin_response,
            "temperature": baseline_temperature
        }
     
    @classmethod 
    def from_profile(cls, profile):
        # Here we can creat the participant based on the generators profile dictionary
        return cls(
            participant_id=profile["participant_id"],
            baseline_heart_rate=profile["baseline_heart_rate"],
            baseline_skin_response=profile["baseline_skin_response"],
            baseline_temperature=profile["baseline_temperature"]
        )
    
    @property
    # Return a copy of the reference attributes as a dictionary
    def reference(self):
        return dict(self._reference)
    
    # Here we update the reference attributes of the participant
    def update_reference(self, field, value):
        if field not in self._reference:
            raise ValueError(f"Field '{field}' is not a valid reference attribute.")
        if value is None or value < 0:
            raise ValueError(f"Value for '{field}' must be a non-negative number.")
        self._reference[field] = value

# Third class as requiremnt from the assignment description        
class Session:
    def __init__(self, participant, observations):
        self.participant = participant
        self.observations = observations
    
    # Return the list of valid observations for the session
    def valid_observations(self):
        return [obs for obs in self.observations if obs.is_valid()[0]]
    
    # Return the count of invalid observations for the session
    def invalid_count(self):
        return len([obs for obs in self.observations if not obs.is_valid()[0]])

# FOurth class as by the requirements of the assignment description
class SessionAnalyzer:
    
    # Min number of observations this can be tweaked, not sure what a good number is
    MIN_USABLE_OBSERVATIONS = 3
    
    # Initialize the session analyzer with a session instance
    def __init__(self, session):
        self.session = session
    
    # Analyze the session and return a summary of the results
    def analyze(self):
        usable = self.session.valid_observations()
        # Initialize the result dictionary with basic session information
        result = {
            "participant_id": self.session.participant.participant_id,
            "total_observations": len(self.session.observations),
            "usable_observations": len(usable),
            "rejected_observations": self.session.invalid_count()
        }
        
        # Check if there are enough usable observations for meaningful analysis
        if len(usable) < self.MIN_USABLE_OBSERVATIONS:
            result["classification"] = "insufficient_data"
            result["recovery_detected"] = False
            result["reasoning"] = (
                f"Fewer than {self.MIN_USABLE_OBSERVATIONS} usable observations were recorded."
            )
            
            return result
        
        # Extract heart rates and activity levels from usable observations
        heart_rates = [obs.heart_rate for obs in usable]
        activity_levels = [obs.activity_level for obs in usable]
        
        # Compute summary statistics for heart rates and activity levels
        hr_summary =  compute_summary_stats(heart_rates)
        activity_summary = compute_summary_stats(activity_levels)
        
        # Store the computed summary statistics in the result dictionary
        result["heart_rate_summary"] = hr_summary
        result["activity_level_summary"] = activity_summary

        # Compare the average heart rate with the reference heart rate
        reference_hr = self.session.participant.reference["heart_rate"]
        result["heart_rate_vs_reference"] = round(hr_summary["average"] - reference_hr, 2)
        
        # Detect recovery and classify the session intensity
        recovering = detect_recovery(usable)
        classification = classify_intensity(
            hr_summary["average"], reference_hr, activity_summary["average"]
        )
        
        # Adjust classification if recovery is detected and the session is not resting
        if recovering and classification != "resting":
            classification = "recovering"
        
        # Store the final classification and recovery status in the result dictionary
        result["classification"] = classification
        result["recovery_detected"] = recovering
        result["reasoning"] = build_reasoning(classification, hr_summary, reference_hr, recovering)
        
        return result
        
        
"""
This part will include the standalone functions used for calculation, validation and presentation
as explained in the assingment paper
"""
   
# Statistical functions for analyzing fitness session data
def compute_summary_stats(values):
    #Return the average, minimum and maximum of a list of numbers.
    return {
        "average": round(statistics.mean(values), 2),
        "minimum": round(min(values), 2),
        "maximum": round(max(values), 2),
    }
 
# Recovery detection based on heart rate and activity trends
def detect_recovery(observations):
    #Check whether heart rate and activity decline in the second half of
    #a session compared with the first half.
    if len(observations) < 6:
        return False
    
    # Split the observations into two halves for comparison.
    midpoint = len(observations) // 2
    first_half = observations[:midpoint]
    second_half = observations[midpoint:]
 
    # Compute the average heart rate and activity level for each half.
    first_hr = statistics.mean(obs.heart_rate for obs in first_half)
    second_hr = statistics.mean(obs.heart_rate for obs in second_half)
    first_activity = statistics.mean(obs.activity_level for obs in first_half)
    second_activity = statistics.mean(obs.activity_level for obs in second_half)
 
    # Determine if there is a significant drop in heart rate and activity level in the second half.
    return second_hr < first_hr - 5 and second_activity < first_activity - 0.1

# Intensity classification based on heart rate and activity level
def classify_intensity(avg_heart_rate, reference_heart_rate, avg_activity):
    #Classify a session as resting, moderate activity or high activity,
    #based on how far heart rate and activity are from the personal baseline.

    # Calculate the gap between the average heart rate and the reference heart rate.
    hr_gap = avg_heart_rate - reference_heart_rate
    if hr_gap <= 10 and avg_activity <= 0.25:
        return "resting"
    if hr_gap <= 35 and avg_activity <= 0.65:
        return "moderate activity"
    return "high activity"

# Console report formatting for session results
def format_console_report(result):
    #Turn a result dictionary into a printable console report.
    lines = ["=== Fitness Session Report ===", f"Participant: {result['participant_id']}"]
    lines.append(
        f"Observations received: {result['total_observations']} | "
        f"Usable: {result['usable_observations']} | "
        f"Rejected: {result['rejected_observations']}"
    )

    # Handle the case where there is insufficient data for classification.
    if result["classification"] == "insufficient_data":
        lines.append("")
        lines.append("Classification: INSUFFICIENT DATA")
        lines.append(f"Reasoning: {result['reasoning']}")
        return "\n".join(lines)

    # Summarize heart rate and activity level for the report.
    hr = result["heart_rate_summary"]
    act = result["activity_level_summary"]
    lines.append("")
    lines.append(f"Heart rate   - avg: {hr['average']} | min: {hr['minimum']} | max: {hr['maximum']}")
    lines.append(f"Activity lvl - avg: {act['average']} | min: {act['minimum']} | max: {act['maximum']}")
    lines.append(f"Heart rate vs reference: {result['heart_rate_vs_reference']:+} bpm")
    lines.append("")
    lines.append(f"Classification: {result['classification'].upper()}")
    lines.append(f"Recovery detected: {'Yes' if result['recovery_detected'] else 'No'}")
    lines.append(f"Reasoning: {result['reasoning']}")
    return "\n".join(lines)

# Reasoning builder for session classification
def build_reasoning(classification, hr_summary, reference_hr, recovering):
    # Produce a short human-readable explanation for a classification.
    gap = round(hr_summary["average"] - reference_hr, 1)
    text = f"Average heart rate was {hr_summary['average']} bpm ({gap:+} bpm vs reference)."
    if recovering:
        text += " Heart rate and activity declined toward the end of the session, indicating recovery."
    elif classification == "resting":
        text += " Values stayed close to the participant's resting reference."
    else:
        text += " Values remained elevated with no clear downward trend."
    return text

# Session builder for generating test data
def build_session(scenario, participant_id="P001", seed=42, number_of_windows=12):
    """Generate data for one scenario and wrap it into a Session object."""
    profile, raw_observations = generate_fitness_data(
        participant_id=participant_id,
        scenario=scenario,
        seed=seed,
        number_of_windows=number_of_windows,
    )
    participant = Participant.from_profile(profile)
    observations = [Observation.from_dict(obs) for obs in raw_observations]
    return Session(participant, observations)

# Main function to run the analysis on all scenarios and print the reports.
def main():
    scenarios = ("resting", "moderate_activity", "high_activity", "recovery", "poor_quality")
    for scenario in scenarios:
        session = build_session(scenario, seed=1)
        result = SessionAnalyzer(session).analyze()

        print(format_console_report(result))
        print("="*50)  # Separator between scenarios for readability
 
 
if __name__ == "__main__":
    main()