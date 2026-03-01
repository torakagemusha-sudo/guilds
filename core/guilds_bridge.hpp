/**
 * GUILDS Bridge - C++ Header-Only Integration Library
 * ====================================================
 *
 * Provides C++ integration for GUILDS-generated GUIs, enabling:
 *   - Callback registration for UI actions
 *   - Phase and claim updates
 *   - Failure injection and clearing
 *   - Flow control
 *   - Optional WebSocket client for remote control
 *
 * Usage:
 *   #include "guilds_bridge.hpp"
 *
 *   Guilds::Bridge bridge;
 *   bridge.onAction([](const std::string& name, const Guilds::ActionData& data) {
 *       std::cout << "Action: " << name << std::endl;
 *   });
 *   bridge.onPhaseChange([](Guilds::Phase phase) {
 *       std::cout << "Phase: " << Guilds::phaseToString(phase) << std::endl;
 *   });
 *
 * License: MIT
 */

#ifndef GUILDS_BRIDGE_HPP
#define GUILDS_BRIDGE_HPP

#include <functional>
#include <string>
#include <map>
#include <vector>
#include <memory>
#include <mutex>
#include <any>

namespace Guilds {

// ---------------------------------------------------------------------------
// Phase Enumeration
// ---------------------------------------------------------------------------

enum class Phase {
    Idle = 0,
    Orient,
    Execute,
    Verify,
    Integrate,
    Recover,
    COUNT
};

inline const char* phaseToString(Phase phase) {
    static const char* names[] = {
        "idle", "orient", "execute", "verify", "integrate", "recover"
    };
    int idx = static_cast<int>(phase);
    if (idx >= 0 && idx < static_cast<int>(Phase::COUNT)) {
        return names[idx];
    }
    return "unknown";
}

inline Phase stringToPhase(const std::string& name) {
    if (name == "idle")      return Phase::Idle;
    if (name == "orient")    return Phase::Orient;
    if (name == "execute")   return Phase::Execute;
    if (name == "verify")    return Phase::Verify;
    if (name == "integrate") return Phase::Integrate;
    if (name == "recover")   return Phase::Recover;
    return Phase::Idle;
}


// ---------------------------------------------------------------------------
// Failure Types
// ---------------------------------------------------------------------------

enum class FailureKind {
    Degraded,
    Blocked,
    Lost,
    Partial,
    Stale,
    Recovering,
    Cascade,
    Unknown,
    Fatal,
    Silent
};

inline const char* failureToString(FailureKind kind) {
    static const char* names[] = {
        "degraded", "blocked", "lost", "partial", "stale",
        "recovering", "cascade", "unknown", "fatal", "silent"
    };
    return names[static_cast<int>(kind)];
}


// ---------------------------------------------------------------------------
// Data Structures
// ---------------------------------------------------------------------------

struct ActionData {
    std::string actionName;
    Phase phase = Phase::Idle;
    std::map<std::string, std::string> metadata;
};

struct ClaimData {
    std::string value;
    std::string certainty = "unknown";
    std::string stakes = "medium";
    bool isStale = false;
};

struct FlowData {
    int stepIndex = 0;
    std::string stepName;
    std::string state = "idle";
    int64_t elapsedMs = 0;
    bool stalled = false;
    std::string terminal;  // Empty if still running
};

struct FailureData {
    FailureKind kind = FailureKind::Unknown;
    std::string vessel;
    std::string cause;
    std::vector<std::string> propagatedTo;
    bool cascadeBlocked = false;
};


// ---------------------------------------------------------------------------
// Callback Types
// ---------------------------------------------------------------------------

using ActionCallback = std::function<void(const std::string& name, const ActionData& data)>;
using PhaseCallback = std::function<void(Phase newPhase)>;
using ClaimCallback = std::function<void(const std::string& name, const ClaimData& data)>;
using FlowCallback = std::function<void(const std::string& name, const FlowData& data)>;
using FailureCallback = std::function<void(const FailureData& failure)>;


// ---------------------------------------------------------------------------
// Bridge Interface
// ---------------------------------------------------------------------------

/**
 * Abstract bridge interface for GUILDS integration.
 * Implementations can be local (direct) or remote (WebSocket).
 */
class IBridge {
public:
    virtual ~IBridge() = default;

    // Phase control
    virtual void setPhase(Phase phase) = 0;
    virtual Phase getPhase() const = 0;

    // Claim management
    virtual void setClaim(const std::string& name, const ClaimData& data) = 0;
    virtual ClaimData getClaim(const std::string& name) const = 0;

    // Failure management
    virtual void injectFailure(const std::string& vessel, FailureKind kind,
                               const std::string& cause = "") = 0;
    virtual void clearFailure(const std::string& vessel) = 0;

    // Flow control
    virtual void startFlow(const std::string& name) = 0;
    virtual void stopFlow(const std::string& name, const std::string& terminal = "success") = 0;

    // Callbacks
    virtual void onAction(ActionCallback callback) = 0;
    virtual void onPhaseChange(PhaseCallback callback) = 0;
    virtual void onClaimUpdate(ClaimCallback callback) = 0;
    virtual void onFlowUpdate(FlowCallback callback) = 0;
    virtual void onFailure(FailureCallback callback) = 0;
};


// ---------------------------------------------------------------------------
// Local Bridge Implementation
// ---------------------------------------------------------------------------

/**
 * Local bridge for direct integration with GUILDS UI.
 * Use this when the UI and application are in the same process.
 */
class Bridge : public IBridge {
public:
    Bridge() = default;
    ~Bridge() override = default;

    // Phase control
    void setPhase(Phase phase) override {
        std::lock_guard<std::mutex> lock(m_mutex);
        Phase oldPhase = m_currentPhase;
        m_currentPhase = phase;

        if (m_phaseCallback && phase != oldPhase) {
            m_phaseCallback(phase);
        }
    }

    Phase getPhase() const override {
        std::lock_guard<std::mutex> lock(m_mutex);
        return m_currentPhase;
    }

    // Claim management
    void setClaim(const std::string& name, const ClaimData& data) override {
        std::lock_guard<std::mutex> lock(m_mutex);
        m_claims[name] = data;

        if (m_claimCallback) {
            m_claimCallback(name, data);
        }
    }

    void setClaim(const std::string& name, const std::string& value,
                  const std::string& certainty = "unknown") {
        ClaimData data;
        data.value = value;
        data.certainty = certainty;
        setClaim(name, data);
    }

    ClaimData getClaim(const std::string& name) const override {
        std::lock_guard<std::mutex> lock(m_mutex);
        auto it = m_claims.find(name);
        if (it != m_claims.end()) {
            return it->second;
        }
        return ClaimData{};
    }

    // Failure management
    void injectFailure(const std::string& vessel, FailureKind kind,
                       const std::string& cause = "") override {
        std::lock_guard<std::mutex> lock(m_mutex);

        FailureData failure;
        failure.kind = kind;
        failure.vessel = vessel;
        failure.cause = cause;
        m_activeFailures[vessel] = failure;

        if (m_failureCallback) {
            m_failureCallback(failure);
        }
    }

    void clearFailure(const std::string& vessel) override {
        std::lock_guard<std::mutex> lock(m_mutex);
        m_activeFailures.erase(vessel);
    }

    bool hasFailure(const std::string& vessel) const {
        std::lock_guard<std::mutex> lock(m_mutex);
        return m_activeFailures.find(vessel) != m_activeFailures.end();
    }

    // Flow control
    void startFlow(const std::string& name) override {
        std::lock_guard<std::mutex> lock(m_mutex);
        FlowData& flow = m_flows[name];
        flow.stepIndex = 0;
        flow.state = "running";
        flow.terminal.clear();

        if (m_flowCallback) {
            m_flowCallback(name, flow);
        }
    }

    void stopFlow(const std::string& name, const std::string& terminal = "success") override {
        std::lock_guard<std::mutex> lock(m_mutex);
        if (m_flows.find(name) != m_flows.end()) {
            m_flows[name].terminal = terminal;
            m_flows[name].state = "complete";

            if (m_flowCallback) {
                m_flowCallback(name, m_flows[name]);
            }
        }
    }

    FlowData getFlow(const std::string& name) const {
        std::lock_guard<std::mutex> lock(m_mutex);
        auto it = m_flows.find(name);
        if (it != m_flows.end()) {
            return it->second;
        }
        return FlowData{};
    }

    // Callbacks
    void onAction(ActionCallback callback) override {
        std::lock_guard<std::mutex> lock(m_mutex);
        m_actionCallback = std::move(callback);
    }

    void onPhaseChange(PhaseCallback callback) override {
        std::lock_guard<std::mutex> lock(m_mutex);
        m_phaseCallback = std::move(callback);
    }

    void onClaimUpdate(ClaimCallback callback) override {
        std::lock_guard<std::mutex> lock(m_mutex);
        m_claimCallback = std::move(callback);
    }

    void onFlowUpdate(FlowCallback callback) override {
        std::lock_guard<std::mutex> lock(m_mutex);
        m_flowCallback = std::move(callback);
    }

    void onFailure(FailureCallback callback) override {
        std::lock_guard<std::mutex> lock(m_mutex);
        m_failureCallback = std::move(callback);
    }

    // Trigger action (called by UI)
    void triggerAction(const std::string& name) {
        std::lock_guard<std::mutex> lock(m_mutex);
        if (m_actionCallback) {
            ActionData data;
            data.actionName = name;
            data.phase = m_currentPhase;
            m_actionCallback(name, data);
        }
    }

    void triggerAction(const std::string& name, const ActionData& data) {
        std::lock_guard<std::mutex> lock(m_mutex);
        if (m_actionCallback) {
            m_actionCallback(name, data);
        }
    }

private:
    mutable std::mutex m_mutex;
    Phase m_currentPhase = Phase::Idle;
    std::map<std::string, ClaimData> m_claims;
    std::map<std::string, FlowData> m_flows;
    std::map<std::string, FailureData> m_activeFailures;

    ActionCallback m_actionCallback;
    PhaseCallback m_phaseCallback;
    ClaimCallback m_claimCallback;
    FlowCallback m_flowCallback;
    FailureCallback m_failureCallback;
};


// ---------------------------------------------------------------------------
// Event Builder (Fluent API)
// ---------------------------------------------------------------------------

/**
 * Fluent builder for creating and dispatching events.
 */
class EventBuilder {
public:
    explicit EventBuilder(Bridge& bridge) : m_bridge(bridge) {}

    EventBuilder& action(const std::string& name) {
        m_actionData.actionName = name;
        return *this;
    }

    EventBuilder& phase(Phase p) {
        m_actionData.phase = p;
        return *this;
    }

    EventBuilder& meta(const std::string& key, const std::string& value) {
        m_actionData.metadata[key] = value;
        return *this;
    }

    void dispatch() {
        m_bridge.triggerAction(m_actionData.actionName, m_actionData);
    }

private:
    Bridge& m_bridge;
    ActionData m_actionData;
};


// ---------------------------------------------------------------------------
// Utility Functions
// ---------------------------------------------------------------------------

/**
 * Create a claim with value and certainty.
 */
inline ClaimData makeClaim(const std::string& value,
                           const std::string& certainty = "unknown",
                           const std::string& stakes = "medium") {
    ClaimData data;
    data.value = value;
    data.certainty = certainty;
    data.stakes = stakes;
    return data;
}

/**
 * Create an action data structure.
 */
inline ActionData makeAction(const std::string& name, Phase phase = Phase::Idle) {
    ActionData data;
    data.actionName = name;
    data.phase = phase;
    return data;
}

} // namespace Guilds

#endif // GUILDS_BRIDGE_HPP
