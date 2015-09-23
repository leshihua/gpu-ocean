#include "mockup_sim.h"
#include "../../mgr/src/programoptions.h"
#include <boost/format.hpp>
#include <iostream>
#include <stdexcept>

using namespace std;

struct Simulator::SimulatorImpl
{
    OptionsPtr options;
    int nextStep;
    int finalStep;
    SimulatorImpl(const OptionsPtr &);
};

Simulator::SimulatorImpl::SimulatorImpl(const OptionsPtr &options)
    : options(options)
    , nextStep(-1)
    , finalStep(-1)
{
}

Simulator::Simulator(const OptionsPtr &options)
    : pimpl(new SimulatorImpl(options))
{
}

Simulator::~Simulator()
{
}

void Simulator::init()
{
    pimpl->nextStep = 0;

    //pimpl->finalStep = calculate from options_->duration();
    pimpl->finalStep = 4; // ### for now
}

int Simulator::nextStep() const
{
    return pimpl->nextStep;
}

int Simulator::finalStep() const
{
    return pimpl->finalStep;
}

void Simulator::execNextStep()
{
    if (pimpl->nextStep > pimpl->finalStep)
        throw runtime_error((boost::format("error: next_step_ (%1%) > final_step_ (%2%)") % pimpl->nextStep % pimpl->finalStep).str());

    // executing next step ... TBD

    pimpl->nextStep++;
}

void Simulator::printStatus() const
{
    cout << "Simulator::printStatus(); options: " << *pimpl->options << endl;
}